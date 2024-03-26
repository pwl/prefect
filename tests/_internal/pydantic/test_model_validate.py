from typing import cast

import pytest
from pydantic import BaseModel, ValidationError

from prefect._internal.pydantic._compat import model_validate
from prefect._internal.pydantic._flags import EXPECT_DEPRECATION_WARNINGS


class Model(BaseModel):
    a: int
    b: str


@pytest.mark.skipif(
    EXPECT_DEPRECATION_WARNINGS,
    reason="Valid when pydantic compatibility layer is enabled or when v1 is installed",
)
def test_model_validate():
    model_instance = model_validate(Model, {"a": 1, "b": "test"})

    assert isinstance(model_instance, Model)

    assert cast(Model, model_instance).a == 1

    assert cast(Model, model_instance).b == "test"


@pytest.mark.skipif(
    not EXPECT_DEPRECATION_WARNINGS,
    reason="Only valid when compatibility layer is disabled and v2 is installed",
)
def test_model_validate_with_flag_disabled():
    from pydantic import PydanticDeprecatedSince20

    with pytest.warns(PydanticDeprecatedSince20):
        model_instance = model_validate(Model, {"a": 1, "b": "test"})

    assert cast(Model, model_instance).a == 1

    assert cast(Model, model_instance).b == "test"


@pytest.mark.skipif(
    EXPECT_DEPRECATION_WARNINGS,
    reason="Valid when pydantic compatibility layer is enabled or when v1 is installed",
)
def test_model_validate_with_invalid_model():
    try:
        model_validate(Model, {"a": "not an int", "b": "test"})
    except ValidationError as e:
        errors = e.errors()

        assert len(errors) == 1

        error = errors[0]

        assert error["loc"] == ("a",)
        assert "valid integer" in error["msg"]


@pytest.mark.skipif(
    not EXPECT_DEPRECATION_WARNINGS,
    reason="Only valid when compatibility layer is disabled and v2 is installed",
)
def test_model_validate_with_invalid_model_and_flag_disabled():
    from pydantic import PydanticDeprecatedSince20

    with pytest.warns(PydanticDeprecatedSince20):
        try:
            model_validate(Model, {"a": "not an int", "b": "test"})
        except ValidationError as e:
            errors = e.errors()

            assert len(errors) == 1

            error = errors[0]

            assert error["loc"] == ("a",)
            assert "valid integer" in error["msg"]