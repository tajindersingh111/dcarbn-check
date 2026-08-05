from __future__ import annotations

import ast
from decimal import Decimal, DivisionByZero, InvalidOperation


class FormulaValidationError(ValueError):
    pass


_ALLOWED_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_UNARY_OPERATORS = (ast.UAdd, ast.USub)


def validate_formula(expression: str, allowed_variables: set[str]) -> None:
    if not expression.strip():
        raise FormulaValidationError("Formula expression cannot be blank.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaValidationError("Formula expression is not valid.") from exc
    _validate_node(tree.body, allowed_variables)


def evaluate_formula(
    expression: str,
    variables: dict[str, Decimal],
) -> Decimal:
    validate_formula(expression, set(variables))
    tree = ast.parse(expression, mode="eval")
    try:
        return _evaluate_node(tree.body, variables)
    except (DivisionByZero, InvalidOperation, ZeroDivisionError) as exc:
        raise FormulaValidationError("Formula could not be evaluated safely.") from exc


def _validate_node(node: ast.AST, allowed_variables: set[str]) -> None:
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINARY_OPERATORS):
            raise FormulaValidationError("Formula contains an unsupported operator.")
        _validate_node(node.left, allowed_variables)
        _validate_node(node.right, allowed_variables)
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY_OPERATORS):
            raise FormulaValidationError(
                "Formula contains an unsupported unary operator."
            )
        _validate_node(node.operand, allowed_variables)
        return
    if isinstance(node, ast.Name):
        if node.id not in allowed_variables:
            raise FormulaValidationError(
                f"Formula references undeclared variable {node.id!r}."
            )
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaValidationError("Formula constants must be numeric.")
        return
    raise FormulaValidationError(
        f"Formula contains unsupported syntax: {type(node).__name__}."
    )


def _evaluate_node(
    node: ast.AST,
    variables: dict[str, Decimal],
) -> Decimal:
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left, variables)
        right = _evaluate_node(node.right, variables)
        return _apply_binary_operator(node.op, left, right)
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_node(node.operand, variables)
        return _apply_unary_operator(node.op, value)
    if isinstance(node, ast.Name):
        return variables[node.id]
    if isinstance(node, ast.Constant):
        return Decimal(str(node.value))
    raise FormulaValidationError("Formula contains unsupported syntax.")


def _apply_binary_operator(
    operator: ast.operator,
    left: Decimal,
    right: Decimal,
) -> Decimal:
    if isinstance(operator, ast.Add):
        return left + right
    if isinstance(operator, ast.Sub):
        return left - right
    if isinstance(operator, ast.Mult):
        return left * right
    if isinstance(operator, ast.Div):
        return left / right
    raise FormulaValidationError("Formula contains an unsupported operator.")


def _apply_unary_operator(
    operator: ast.unaryop,
    value: Decimal,
) -> Decimal:
    if isinstance(operator, ast.UAdd):
        return value
    if isinstance(operator, ast.USub):
        return -value
    raise FormulaValidationError("Formula contains an unsupported unary operator.")
