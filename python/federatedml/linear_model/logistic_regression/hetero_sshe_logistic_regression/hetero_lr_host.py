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

import functools
import operator

import numpy as np

from federatedml.linear_model.logistic_regression.hetero_sshe_logistic_regression.hetero_lr_base import HeteroLRBase
from federatedml.protobuf.generated import lr_model_param_pb2
from federatedml.secureprotol.spdz.secure_matrix.secure_matrix import SecureMatrix
from federatedml.secureprotol.spdz.tensor import fixedpoint_table, fixedpoint_numpy
from federatedml.util import consts, LOGGER
from federatedml.util import fate_operator


class HeteroLRHost(HeteroLRBase):
    def __init__(self):
        super().__init__()
        self.data_batch_count = []
        self.wx_self = None

    # def transfer_pubkey(self):
    #     public_key = self.cipher.public_key
    #     self.transfer_variable.pubkey.remote(public_key, role=consts.GUEST, suffix=("host_pubkey",))
    #     remote_pubkey = self.transfer_variable.pubkey.get(role=consts.GUEST, idx=0,
    #                                                       suffix=("guest_pubkey",))
    #     return remote_pubkey

    def _init_weights(self, model_shape):
        # init_param_obj = copy.deepcopy(self.init_param_obj)
        # init_param_obj.fit_intercept = False
        self.init_param_obj.fit_intercept = False
        return self.initializer.init_model(model_shape, init_params=self.init_param_obj)

    def _cal_z_in_share(self, w_self, w_remote, features, suffix):
        z1 = features.dot_local(w_self)

        za_suffix = ("za",) + suffix
        za_share = self.secure_matrix_obj.secure_matrix_mul(features,
                                                            tensor_name=".".join(za_suffix),
                                                            cipher=None,
                                                            suffix=za_suffix)

        zb_suffix = ("zb",) + suffix
        zb_share = self.secure_matrix_obj.secure_matrix_mul(w_remote,
                                                            tensor_name=".".join(zb_suffix),
                                                            cipher=self.cipher,
                                                            suffix=zb_suffix)

        z = z1 + za_share + zb_share
        return z

    def cal_prediction(self, w_self, w_remote, features, spdz, suffix):
        if not self.review_every_iter:
            z = self._cal_z_in_share(w_self, w_remote, features, suffix)
        else:
            z = features.dot_local(self.model_weights.coef_)

        self.wx_self = z
        self.secure_matrix_obj.share_encrypted_matrix(suffix=suffix,
                                                      is_remote=True,
                                                      cipher=self.cipher,
                                                      z=z)

        tensor_name = ".".join(("sigmoid_z",) + suffix)
        shared_sigmoid_z = SecureMatrix.from_source(tensor_name,
                                                    self.other_party,
                                                    self.cipher,
                                                    self.fixedpoint_encoder.n,
                                                    self.fixedpoint_encoder)

        return shared_sigmoid_z

    def compute_gradient(self, error: fixedpoint_table.FixedPointTensor, features, suffix):
        encoded_1_n = self.encoded_batch_num[int(suffix[1])]

        ga = error.dot_local(features)
        LOGGER.debug(f"ga: {ga}, encoded_1_n: {encoded_1_n}")
        ga = ga * encoded_1_n

        zb_suffix = ("ga2",) + suffix
        ga2_1 = self.secure_matrix_obj.secure_matrix_mul(features,
                                                         tensor_name=".".join(zb_suffix),
                                                         cipher=None,
                                                         suffix=zb_suffix)

        LOGGER.debug(f"ga2_1: {ga2_1}")

        ga_new = ga + ga2_1

        tensor_name = ".".join(("encrypt_g",) + suffix)
        gb1 = SecureMatrix.from_source(tensor_name,
                                       self.other_party,
                                       self.cipher,
                                       self.fixedpoint_encoder.n,
                                       self.fixedpoint_encoder,
                                       is_fixedpoint_table=False)

        LOGGER.debug(f"gb1: {gb1}")

        return ga_new, gb1

    def compute_loss(self, suffix):
        """
          Use Taylor series expand log loss:
          Loss = - y * log(h(x)) - (1-y) * log(1 - h(x)) where h(x) = 1/(1+exp(-wx))
          Then loss' = - (1/N)*∑(log(1/2) - 1/2*wx + ywx + 1/8(wx)^2)
        """
        wx_self_square = (self.wx_self * self.wx_self).reduce(operator.add)
        LOGGER.debug(f"wx_self_square: {wx_self_square}")

        self.secure_matrix_obj.share_encrypted_matrix(suffix=suffix,
                                                      is_remote=True,
                                                      cipher=self.cipher,
                                                      wx_self_square=wx_self_square)

        tensor_name = ".".join(("shared_loss",) + suffix)
        share_loss = SecureMatrix.from_source(tensor_name=tensor_name,
                                              source=self.other_party,
                                              cipher=self.cipher,
                                              q_field=self.fixedpoint_encoder.n,
                                              encoder=self.fixedpoint_encoder,
                                              is_fixedpoint_table=False)

        LOGGER.debug(f"share_loss: {share_loss}")

        # todo: dylan, review & unreview loss_norm;
        if self.review_every_iter:
            loss_norm = self.optimizer.loss_norm(self.model_weights)
            if loss_norm:
                share_loss += loss_norm/3.0
        else:
            pass

        LOGGER.debug(f"share_loss+loss_norm: {share_loss}")

        share_loss.broadcast_reconstruct_share(tensor_name=f"share_loss_{suffix}")

    # def compute_loss_old(self, spdz, suffix):
    #     tensor_name = ".".join(("shared_wx",) + suffix)
    #     shared_wx = SecureMatrix.from_source(tensor_name,
    #                                          self.other_party,
    #                                          self.cipher,
    #                                          self.fixedpoint_encoder.n,
    #                                          self.fixedpoint_encoder)
    #
    #     LOGGER.debug(f"share_wx: {type(shared_wx)}, shared_y: {type(self.shared_y)}")
    #
    #     wxy = spdz.dot(shared_wx, self.shared_y, ("wxy",) + suffix).get()
    #
    #     LOGGER.debug(f"wxy_value: {wxy}")
    #
    #     wx_guest, wx_square_guest = self.share_encrypted_value(suffix=suffix, is_remote=False,
    #                                                            wx=None, wx_square=None)
    #
    #     encrypted_wx = shared_wx + wx_guest
    #     encrypted_wx_square = shared_wx * shared_wx + wx_square_guest + 2 * shared_wx * wx_guest
    #     encoded_1_n = self.encoded_batch_num[int(suffix[2])]
    #
    #     LOGGER.debug(f"encoded_batch_num: {self.encoded_batch_num}, suffix: {suffix}")
    #
    #     LOGGER.debug(f"tmc, type: {encrypted_wx_square}, {encrypted_wx}, {encoded_1_n}, {wxy}")
    #
    #     loss = ((0.125 * encrypted_wx_square - 0.5 * encrypted_wx).reduce(operator.add) +
    #             wxy) * encoded_1_n * -1 - np.log(0.5)
    #
    #     loss_norm = self.optimizer.loss_norm(self.model_weights)
    #     if loss_norm is not None:
    #         loss += loss_norm
    #     LOGGER.debug(f"loss: {loss}")
    #     self.transfer_variable.loss.remote(loss[0][0], suffix=suffix)

    def check_converge_by_weights(self, spdz, last_w, new_w, suffix):
        if self.review_every_iter:
            return self._review_every_iter_check(last_w, new_w, suffix)
        else:
            return self._unreview_every_iter_check(spdz, last_w, new_w, suffix)

    def _review_every_iter_check(self, last_w, new_w, suffix):
        square_sum = np.sum((last_w - new_w) ** 2)
        self.converge_transfer_variable.square_sum.remote(square_sum, role=consts.GUEST, idx=0, suffix=suffix)
        return self.converge_transfer_variable.converge_info.get(idx=0, suffix=suffix)

    def _unreview_every_iter_check(self, spdz, last_w, new_w, suffix):
        last_w_self, last_w_remote = last_w
        w_self, w_remote = new_w
        grad_self = w_self - last_w_self
        grad_remote = w_remote - last_w_remote
        grad_encode = np.hstack((grad_self.value, grad_remote.value))
        grad_encode = np.array([grad_encode])
        grad_tensor_name = ".".join(("check_converge_grad",) + suffix)
        grad_tensor = fixedpoint_numpy.FixedPointTensor(value=grad_encode,
                                                        q_field=self.fixedpoint_encoder.n,
                                                        endec=self.fixedpoint_encoder,
                                                        tensor_name=grad_tensor_name)

        grad_tensor_transpose_name = ".".join(("check_converge_grad_transpose",) + suffix)
        grad_tensor_transpose = fixedpoint_numpy.FixedPointTensor(value=grad_encode.T,
                                                                  q_field=self.fixedpoint_encoder.n,
                                                                  endec=self.fixedpoint_encoder,
                                                                  tensor_name=grad_tensor_transpose_name)

        grad_norm_tensor_name = ".".join(("check_converge_grad_norm",) + suffix)

        grad_norm = spdz.dot(grad_tensor, grad_tensor_transpose, target_name=grad_norm_tensor_name).get()
        LOGGER.info(f"gradient spdz dot.get: {grad_norm}")
        weight_diff = np.sqrt(grad_norm[0][0])
        LOGGER.info("iter: {}, weight_diff:{}, is_converged: {}".format(self.n_iter_,
                                                                        weight_diff, self.is_converged))
        is_converge = False
        if weight_diff < self.model_param.tol:
            is_converge = True
        return is_converge

    def predict(self, data_instances):
        LOGGER.info("Start predict ...")
        self._abnormal_detection(data_instances)
        data_instances = self.align_data_header(data_instances, self.header)
        if self.need_one_vs_rest:
            self.one_vs_rest_obj.predict(data_instances)
            return

        LOGGER.debug(f"Before_predict_review_strategy: {self.model_param.reveal_strategy},"
                     f" {self.is_respectively_reveal}")

        def _vec_dot(v, coef, intercept):
            return fate_operator.vec_dot(v.features, coef) + intercept

        f = functools.partial(_vec_dot,
                              coef=self.model_weights.coef_,
                              intercept=self.model_weights.intercept_)
        prob_host = data_instances.mapValues(f)
        self.transfer_variable.host_prob.remote(prob_host, role=consts.GUEST, idx=0)
        LOGGER.info("Remote probability to Guest")

    # def _respectively_predict(self, data_instances):
    #     self.transfer_variable.host_prob.disable_auto_clean()
    #
    #     def _vec_dot(v, coef, intercept):
    #         return fate_operator.vec_dot(v.features, coef) + intercept
    #
    #     f = functools.partial(_vec_dot,
    #                           coef=self.model_weights.coef_,
    #                           intercept=self.model_weights.intercept_)
    #     prob_host = data_instances.mapValues(f)
    #     self.transfer_variable.host_prob.remote(prob_host, role=consts.GUEST, idx=0)
    #     LOGGER.info("Remote probability to Guest")
    #
    # def _unbalanced_predict(self, data_instances):
    #     encrypted_host_weights = self.transfer_variable.encrypted_host_weights.get(idx=-1)[0]
    #     prob_host = data_instances.mapValues(lambda v: fate_operator.vec_dot(v.features, encrypted_host_weights))
    #     self.transfer_variable.host_prob.remote(prob_host, role=consts.GUEST, idx=0)
    #     LOGGER.info("Remote probability to Guest")

    # def _get_param(self):
    #     single_result = self.get_single_model_param()
    #     single_result['need_one_vs_rest'] = False
    #     param_protobuf_obj = lr_model_param_pb2.LRModelParam(**single_result)
    #     return param_protobuf_obj

    def _get_param(self):
        if self.need_cv:
            param_protobuf_obj = lr_model_param_pb2.LRModelParam()
            return param_protobuf_obj

        self.header = self.header if self.header else []
        LOGGER.debug("In get_param, self.need_one_vs_rest: {}".format(self.need_one_vs_rest))

        if self.need_one_vs_rest:
            # one_vs_rest_class = list(map(str, self.one_vs_rest_obj.classes))
            one_vs_rest_result = self.one_vs_rest_obj.save(lr_model_param_pb2.SingleModel)
            single_result = {'header': self.header, 'need_one_vs_rest': True, "best_iteration": -1}
        else:
            one_vs_rest_result = None
            single_result = self.get_single_model_param()
            single_result['need_one_vs_rest'] = False
        single_result['one_vs_rest_result'] = one_vs_rest_result

        param_protobuf_obj = lr_model_param_pb2.LRModelParam(**single_result)

        return param_protobuf_obj
