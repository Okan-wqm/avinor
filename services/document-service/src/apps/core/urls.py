from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'categories', DocumentCategoryViewSet, basename='category')
# router.register(r'documents', DocumentViewSet, basename='document')
# router.register(r'versions', DocumentVersionViewSet, basename='version')
# router.register(r'shares', DocumentShareViewSet, basename='share')

urlpatterns = [
    path('', include(router.urls)),
]
