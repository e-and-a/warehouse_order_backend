from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.views import AuditLogViewSet
from apps.catalog.views import CategoryViewSet, ProductViewSet
from apps.orders.views import CustomerViewSet, OrderViewSet
from apps.users.views import UserViewSet
from apps.warehouse.views import StockItemViewSet, WarehouseViewSet
from config.forms import EmailAuthenticationForm
from config.views import DashboardView, OrdersPageView, ProductsPageView, StockPageView


router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("categories", CategoryViewSet, basename="categories")
router.register("products", ProductViewSet, basename="products")
router.register("warehouses", WarehouseViewSet, basename="warehouses")
router.register("stock", StockItemViewSet, basename="stock")
router.register("customers", CustomerViewSet, basename="customers")
router.register("orders", OrderViewSet, basename="orders")
router.register("audit-log", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("products/", ProductsPageView.as_view(), name="products-page"),
    path("stock/", StockPageView.as_view(), name="stock-page"),
    path("orders/", OrdersPageView.as_view(), name="orders-page"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include(router.urls)),
]
