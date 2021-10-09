#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import io
import os
from typing import Iterable

from pyarrow import fs

from fate_arch.common import hdfs_utils
from fate_arch.common.log import getLogger
from fate_arch.storage import StorageEngine, HDFSStoreType
from fate_arch.storage import StorageTableBase

LOGGER = getLogger()


class StorageTable(StorageTableBase):
    def __init__(self,
                 address=None,
                 name: str = None,
                 namespace: str = None,
                 partitions: int = None,
                 store_type: HDFSStoreType = None,
                 options=None):
        super(StorageTable, self).__init__(name=name, namespace=namespace)
        self._address = address
        self._name = name
        self._namespace = namespace
        self._partitions = partitions if partitions else 1
        self._store_type = store_type if store_type else HDFSStoreType.DISK
        self._options = options if options else {}
        self._engine = StorageEngine.HDFS

        # tricky way to load libhdfs
        try:
            from pyarrow import HadoopFileSystem
            HadoopFileSystem(self._path)
        except Exception as e:
            LOGGER.warning(f"load libhdfs failed: {e}")
        self._hdfs_client = fs.HadoopFileSystem.from_uri(self._path)

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def address(self):
        return self._address

    @property
    def engine(self):
        return self._engine

    @property
    def store_type(self):
        return self._store_type

    @property
    def partitions(self):
        return self._partitions

    @property
    def options(self):
        return self._options

    def _put_all(self, kv_list: Iterable, append=True, assume_file_exist=False, **kwargs):
        LOGGER.info(f"put in hdfs file: {self._path}")
        if append and (assume_file_exist or self._exist()):
            stream = self._hdfs_client.open_append_stream(path=self._path, compression=None)
        else:
            stream = self._hdfs_client.open_output_stream(path=self._path, compression=None)

        # todo: when append, counter is not right;
        counter = 0
        with io.TextIOWrapper(stream) as writer:
            for k, v in kv_list:
                writer.write(hdfs_utils.serialize(k, v))
                writer.write(hdfs_utils.NEWLINE)
                counter = counter + 1
        self._meta.update_metas(count=counter)

    def _collect(self, **kwargs) -> list:
        for line in self._as_generator():
            yield hdfs_utils.deserialize(line.rstrip())

    def _read(self) -> list:
        for line in self._as_generator():
            yield line

    def _destroy(self):
        self._hdfs_client.delete_file(self._path)

    def _count(self):
        count = 0
        for _ in self._as_generator():
            count += 1
        return count

    def save_as(self, address, partitions=None, name=None, namespace=None, schema=None, **kwargs):
        self._hdfs_client.copy_file(src=self._path, dst=address.path)
        table = StorageTable(address=address, partitions=partitions, name=name, namespace=namespace, **kwargs)
        table.create_meta(**kwargs)
        return table

    def check_address(self):
        return self._exist()

    def close(self):
        pass

    @property
    def _path(self) -> str:
        return f"{self._address.name_node}/{self._address.path}"

    def _exist(self):
        info = self._hdfs_client.get_file_info([self._path])[0]
        return info.type != fs.FileType.NotFound

    def _as_generator(self):
        info = self._hdfs_client.get_file_info([self._path])[0]
        if info.type == fs.FileType.NotFound:
            raise FileNotFoundError(f"file {self._path} not found")

        elif info.type == fs.FileType.File:
            with io.TextIOWrapper(buffer=self._hdfs_client.open_input_stream(self._path),
                                  encoding="utf-8") as reader:
                for line in reader:
                    yield line

        else:
            selector = fs.FileSelector(os.path.join("/", self._address.path))
            file_infos = self._hdfs_client.get_file_info(selector)
            for file_info in file_infos:
                if file_info.base_name == "_SUCCESS":
                    continue
                assert file_info.is_file, f"{self._path} is directory contains a subdirectory: {file_info.path}"
                with io.TextIOWrapper(
                        buffer=self._hdfs_client.open_input_stream(f"{self._address.name_node}/{file_info.path}"),
                        encoding="utf-8") as reader:
                    for line in reader:
                        yield line
