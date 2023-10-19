import inspect
from typing import Any, Dict, List, Optional, Tuple, Type, _GenericAlias  # type: ignore[attr-defined]

from pait import _pydanitc_adapter
from pait.util import create_pydantic_model
from pydantic import BaseModel

from grpc_gateway.model import field_validator

__all__ = ["rebuild_message_type", "rebuild_dict"]


# flake8: noqa: C901
if _pydanitc_adapter.is_v1:
    from pydantic import root_validator

    def rebuild_message_type(
        raw_type: Type,
        route_func_name: str,
        exclude_column_name: Optional[list] = None,
        nested: Optional[list] = None,
    ) -> Type:
        if not exclude_column_name and not nested:
            return raw_type
        if exclude_column_name:
            if not issubclass(raw_type, BaseModel):
                raise TypeError("The value must be Base Model")
            raw_pydantic_model: Type[BaseModel] = raw_type
            annotation_dict: Dict[str, Tuple[Type, Any]] = {}
            pydantic_validators: Dict[str, Any] = {}
            for column_name, model_field in _pydanitc_adapter.model_fields(raw_pydantic_model).items():
                if column_name in exclude_column_name:
                    continue
                annotation_dict[column_name] = (model_field.type_, model_field.field_info)
                for validators in raw_pydantic_model.__validators__.get(column_name, []):  # type: ignore
                    pydantic_validators[column_name + "_" + validators.func.__name__] = field_validator(
                        column_name,
                        always=validators.always,
                        check_fields=validators.check_fields,
                        each_item=validators.each_item,
                        pre=validators.pre,
                        allow_reuse=True,
                    )(validators.func)

            for _pre_root_validators in raw_pydantic_model.__pre_root_validators__:  # type: ignore
                pydantic_validators[_pre_root_validators.__name__] = root_validator(pre=True, allow_reuse=True)(
                    _pre_root_validators
                )
            for _root_validators in raw_pydantic_model.__post_root_validators__:  # type: ignore
                pydantic_validators[_root_validators.__name__] = root_validator(pre=False, allow_reuse=True)(  # type: ignore
                    _root_validators
                )
            return create_pydantic_model(  # type: ignore[return-value]
                annotation_dict=annotation_dict,
                class_name=(
                    raw_pydantic_model.__name__ + f"{''.join([i.title() for i in route_func_name.split('_')])}Rebuild"
                ),
                pydantic_base=raw_pydantic_model.__base__,  # type: ignore
                pydantic_module=raw_pydantic_model.__module__,
                pydantic_validators=pydantic_validators,
            )
        elif nested:
            for index, column in enumerate(nested):
                if column == "$[]":
                    if not isinstance(raw_type, _GenericAlias) and not getattr(raw_type, "_name", "") == "List":
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a List. "
                        )
                    raw_type = List[  # type: ignore[misc,index]
                        rebuild_message_type(raw_type.__args__[0], route_func_name, nested=nested[1 + index :])
                    ]
                    break
                elif column == "${}":
                    if not isinstance(raw_type, _GenericAlias) and not getattr(raw_type, "_name", "") == "Dict":
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a Dict. "
                        )
                    raw_type = Dict[  # type: ignore[misc,index]
                        raw_type.__args__[0],  # type: ignore[name-defined]
                        rebuild_message_type(raw_type.__args__[1], route_func_name, nested=nested[1 + index :]),
                    ]
                    break
                elif column.startswith("$."):
                    if not issubclass(raw_type, BaseModel):
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a pydantic.BaseModel. "
                        )
                    key = column[2:]
                    fields = _pydanitc_adapter.model_fields(raw_type)

                    fields[key].outer_type_ = rebuild_message_type(
                        fields[key].outer_type_, route_func_name, nested=nested[1 + index :]
                    )

                    break
                else:
                    if not issubclass(raw_type, BaseModel):
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a pydantic.BaseModel. "
                        )
                    raw_type = _pydanitc_adapter.model_fields(raw_type)[column].outer_type_

                if not (inspect.isclass(raw_type) and issubclass(raw_type, BaseModel)):
                    continue
        return raw_type

else:

    def rebuild_message_type(
        raw_type: Type,
        route_func_name: str,
        exclude_column_name: Optional[list] = None,
        nested: Optional[list] = None,
    ) -> Type:
        if not exclude_column_name and not nested:
            return raw_type
        if exclude_column_name:
            if not issubclass(raw_type, BaseModel):
                raise TypeError("The value must be Base Model")
            raw_pydantic_model: Type[BaseModel] = raw_type
            annotation_dict: Dict[str, Tuple[Type, Any]] = {}
            pydantic_validators: Dict[str, Any] = {}
            for column_name, model_field in _pydanitc_adapter.model_fields(raw_pydantic_model).items():
                if column_name in exclude_column_name:
                    continue
                annotation_dict[column_name] = (model_field.annotation, model_field)

            if raw_pydantic_model.__pydantic_decorators__.field_validators:
                from pydantic import field_validator

                for key, validators in raw_pydantic_model.__pydantic_decorators__.field_validators.items():
                    field_set = set(validators.info.fields)
                    field_set -= set(exclude_column_name)
                    pydantic_validators[key] = field_validator(
                        *list(field_set),
                        mode=validators.info.mode,
                        check_fields=validators.info.check_fields,
                    )(validators.func)
            if raw_pydantic_model.__pydantic_decorators__.model_validators:
                from pydantic import model_validator

                for key, model_validators in raw_pydantic_model.__pydantic_decorators__.model_validators.items():
                    pydantic_validators[key] = model_validator(mode=model_validators.info.mode)(model_validators.func)

            return create_pydantic_model(  # type: ignore[return-value]
                annotation_dict=annotation_dict,
                class_name=(
                    raw_pydantic_model.__name__ + f"{''.join([i.title() for i in route_func_name.split('_')])}Rebuild"
                ),
                pydantic_base=raw_pydantic_model.__base__,  # type: ignore
                pydantic_module=raw_pydantic_model.__module__,
                pydantic_validators=pydantic_validators,
            )
        elif nested:
            for index, column in enumerate(nested):
                if column == "$[]":
                    if not isinstance(raw_type, _GenericAlias) and not getattr(raw_type, "_name", "") == "List":
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a List. "
                        )
                    raw_type = List[  # type: ignore[misc,index]
                        rebuild_message_type(raw_type.__args__[0], route_func_name, nested=nested[1 + index :])
                    ]
                    break
                elif column == "${}":
                    if not isinstance(raw_type, _GenericAlias) and not getattr(raw_type, "_name", "") == "Dict":
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a Dict. "
                        )
                    raw_type = Dict[  # type: ignore[misc,index]
                        raw_type.__args__[0],  # type: ignore[name-defined]
                        rebuild_message_type(raw_type.__args__[1], route_func_name, nested=nested[1 + index :]),
                    ]
                    break
                elif column.startswith("$."):
                    if not issubclass(raw_type, BaseModel):
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a pydantic.BaseModel. "
                        )
                    key = column[2:]
                    fields = _pydanitc_adapter.model_fields(raw_type)
                    fields[key].annotation = rebuild_message_type(
                        fields[key].annotation, route_func_name, nested=nested[1 + index :]
                    )
                    break
                else:
                    if not issubclass(raw_type, BaseModel):
                        raise ValueError(  # pragma: no cover
                            f"Parse `{column}({nested})` is error: {raw_type} is not a pydantic.BaseModel. "
                        )
                    raw_type = _pydanitc_adapter.model_fields(raw_type)[column].annotation

                if not (inspect.isclass(raw_type) and issubclass(raw_type, BaseModel)):
                    continue
        return raw_type


def rebuild_dict(
    raw_dict: dict,
    exclude_column_name: Optional[list] = None,
    nested: Optional[list] = None,
) -> Any:
    if not exclude_column_name and not nested:
        return raw_dict
    if exclude_column_name:
        raw_dict = {k: v for k, v in raw_dict.items() if k not in exclude_column_name}
    elif nested:
        for index, column in enumerate(nested):
            if column == "$[]":
                if not isinstance(raw_dict, list):
                    raise ValueError(  # pragma: no cover
                        f"Parse `{column}({nested})` is error: {raw_dict} is not a list. "
                    )
                raw_dict = [rebuild_dict(item, nested=nested[index + 1 :]) for item in raw_dict]
                break
            elif column == "${}":
                if not isinstance(raw_dict, dict):
                    raise ValueError(  # pragma: no cover
                        f"Parse `{column}({nested})` is error: {raw_dict} is not a dict. "
                    )
                raw_dict = {k: rebuild_dict(v, nested=nested[index + 1 :]) for k, v in raw_dict.items()}
                break
            elif column.startswith("$."):
                if not isinstance(raw_dict, dict):
                    raise ValueError(  # pragma: no cover
                        f"Parse `{column}({nested})` is error: {raw_dict} is not a dict. "
                    )
                key = column[2:]
                raw_dict[key] = rebuild_dict(raw_dict[key], nested=nested[index + 1 :])
                break
            else:
                raw_dict = raw_dict[column]
    return raw_dict
