# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: feature-scale-param.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x19\x66\x65\x61ture-scale-param.proto\x12&com.webank.ai.fate.core.mlmodel.buffer\"\xec\x01\n\nScaleParam\x12^\n\x0f\x63ol_scale_param\x18\x01 \x03(\x0b\x32\x45.com.webank.ai.fate.core.mlmodel.buffer.ScaleParam.ColScaleParamEntry\x12\x0e\n\x06header\x18\x02 \x03(\t\x1an\n\x12\x43olScaleParamEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12G\n\x05value\x18\x02 \x01(\x0b\x32\x38.com.webank.ai.fate.core.mlmodel.buffer.ColumnScaleParam:\x02\x38\x01\"Y\n\x10\x43olumnScaleParam\x12\x14\n\x0c\x63olumn_upper\x18\x03 \x01(\x01\x12\x14\n\x0c\x63olumn_lower\x18\x04 \x01(\x01\x12\x0c\n\x04mean\x18\x05 \x01(\x01\x12\x0b\n\x03std\x18\x06 \x01(\x01\x42\x11\x42\x0fScaleParamProtob\x06proto3')



_SCALEPARAM = DESCRIPTOR.message_types_by_name['ScaleParam']
_SCALEPARAM_COLSCALEPARAMENTRY = _SCALEPARAM.nested_types_by_name['ColScaleParamEntry']
_COLUMNSCALEPARAM = DESCRIPTOR.message_types_by_name['ColumnScaleParam']
ScaleParam = _reflection.GeneratedProtocolMessageType('ScaleParam', (_message.Message,), {

  'ColScaleParamEntry' : _reflection.GeneratedProtocolMessageType('ColScaleParamEntry', (_message.Message,), {
    'DESCRIPTOR' : _SCALEPARAM_COLSCALEPARAMENTRY,
    '__module__' : 'feature_scale_param_pb2'
    # @@protoc_insertion_point(class_scope:com.webank.ai.fate.core.mlmodel.buffer.ScaleParam.ColScaleParamEntry)
    })
  ,
  'DESCRIPTOR' : _SCALEPARAM,
  '__module__' : 'feature_scale_param_pb2'
  # @@protoc_insertion_point(class_scope:com.webank.ai.fate.core.mlmodel.buffer.ScaleParam)
  })
_sym_db.RegisterMessage(ScaleParam)
_sym_db.RegisterMessage(ScaleParam.ColScaleParamEntry)

ColumnScaleParam = _reflection.GeneratedProtocolMessageType('ColumnScaleParam', (_message.Message,), {
  'DESCRIPTOR' : _COLUMNSCALEPARAM,
  '__module__' : 'feature_scale_param_pb2'
  # @@protoc_insertion_point(class_scope:com.webank.ai.fate.core.mlmodel.buffer.ColumnScaleParam)
  })
_sym_db.RegisterMessage(ColumnScaleParam)

if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'B\017ScaleParamProto'
  _SCALEPARAM_COLSCALEPARAMENTRY._options = None
  _SCALEPARAM_COLSCALEPARAMENTRY._serialized_options = b'8\001'
  _SCALEPARAM._serialized_start=70
  _SCALEPARAM._serialized_end=306
  _SCALEPARAM_COLSCALEPARAMENTRY._serialized_start=196
  _SCALEPARAM_COLSCALEPARAMENTRY._serialized_end=306
  _COLUMNSCALEPARAM._serialized_start=308
  _COLUMNSCALEPARAM._serialized_end=397
# @@protoc_insertion_point(module_scope)
