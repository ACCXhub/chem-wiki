"""HTTP boundary for M05 Reaction Core and Equation Lab."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .equation import EquationError, EquationMode, balance_equation


class BalanceEquationRequest(BaseModel):
    equation: str = Field(min_length=1, max_length=1000)
    mode: EquationMode = EquationMode.MOLECULAR


class EquationTermDto(BaseModel):
    formula: str
    coefficient: int
    phase: str | None
    charge: int


class ElementConservationDto(BaseModel):
    element: str
    reactants: int
    products: int
    conserved: bool


class ChargeConservationDto(BaseModel):
    reactants: int
    products: int
    conserved: bool


class ConservationDto(BaseModel):
    elements: list[ElementConservationDto]
    charge: ChargeConservationDto | None


class RedoxBoundaryDto(BaseModel):
    state: Literal["not_inferred"] = "not_inferred"
    message: str = "氧化还原解释仅接受经审核元数据，不由配平方程式推断"


class BalanceEquationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    state: Literal["balanced", "no_net_ionic"]
    input_state: Literal["balanced", "unbalanced", "not_applicable"] = Field(alias="inputState")
    mode: EquationMode
    formatted_equation: str = Field(alias="formattedEquation")
    coefficients: list[int]
    reactants: list[EquationTermDto]
    products: list[EquationTermDto]
    conservation: ConservationDto
    message: str | None
    phenomenon: str | None
    redox: RedoxBoundaryDto


router = APIRouter(prefix="/v1/reactions", tags=["reaction-core"])


@router.post("/balance", response_model=BalanceEquationResponse)
def balance(request: BalanceEquationRequest) -> BalanceEquationResponse:
    try:
        result = balance_equation(request.equation, mode=request.mode)
    except EquationError as error:
        raise HTTPException(
            status_code=400,
            detail={"state": error.state, "code": error.code, "message": str(error)},
        ) from error

    split = len(result.reactants)
    reactants = [
        EquationTermDto(
            formula=item.formula,
            coefficient=result.coefficients[index],
            phase=item.phase,
            charge=item.charge,
        )
        for index, item in enumerate(result.reactants)
    ]
    products = [
        EquationTermDto(
            formula=item.formula,
            coefficient=result.coefficients[split + index],
            phase=item.phase,
            charge=item.charge,
        )
        for index, item in enumerate(result.products)
    ]
    return BalanceEquationResponse(
        state=result.state,  # type: ignore[arg-type]
        inputState=result.input_state,
        mode=result.mode,
        formattedEquation=result.formatted_equation,
        coefficients=list(result.coefficients),
        reactants=reactants,
        products=products,
        conservation=ConservationDto(
            elements=[
                ElementConservationDto(
                    element=item.element,
                    reactants=item.reactants,
                    products=item.products,
                    conserved=item.conserved,
                )
                for item in result.elements
            ],
            charge=(
                ChargeConservationDto(
                    reactants=result.charge.reactants,
                    products=result.charge.products,
                    conserved=result.charge.conserved,
                )
                if result.charge
                else None
            ),
        ),
        message=result.message,
        phenomenon=result.phenomenon,
        redox=RedoxBoundaryDto(),
    )
