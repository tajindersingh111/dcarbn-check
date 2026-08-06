from fastapi import APIRouter

from app.api.routes import activities, boundaries, calculations, data_integration, data_review, emission_factors, factor_resolution, health, identity, inventory_governance, methodologies, methodology_governance, operations, organisations, security, scope3_governance, tenants, workflows

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(
    organisations.router,
    prefix="/organisations",
    tags=["organisations"],
)

api_router.include_router(boundaries.router, tags=["boundaries"])

api_router.include_router(
    emission_factors.router,
    tags=["emission factors"],
)

api_router.include_router(
    factor_resolution.router,
    tags=["unit normalisation and factor resolution"],
)

api_router.include_router(activities.router, tags=["activities"])

api_router.include_router(calculations.router, tags=["calculations"])

api_router.include_router(methodologies.router, tags=["methodologies"])
api_router.include_router(methodology_governance.router, tags=["methodology governance"])

api_router.include_router(
    scope3_governance.router,
    tags=["Scope 3 governance"],
)

api_router.include_router(data_integration.router, tags=["DATa integration"])

api_router.include_router(data_review.router, tags=["DATa review"])

api_router.include_router(
    inventory_governance.router,
    tags=["inventory governance and reporting"],
)

api_router.include_router(workflows.router, tags=["frontend workflows"])

api_router.include_router(identity.router, tags=["identity and access"])

api_router.include_router(security.router, tags=["security"])

api_router.include_router(operations.router, tags=["operations"])
