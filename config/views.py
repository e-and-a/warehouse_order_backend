from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import TemplateView
from rest_framework.exceptions import ValidationError

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.catalog.models import Product
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.users.constants import UserRole
from apps.warehouse.models import StockItem, Warehouse
from config.forms import OrderCreateForm, ProductCreateForm


def _has_any_role(user, roles: set[str]) -> bool:
    return bool(user.is_authenticated and (user.is_superuser or user.role in roles))


def _format_validation_error(exc: ValidationError) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return " ".join(f"{key}: {value}" for key, value in detail.items())
    if isinstance(detail, list):
        return " ".join(str(item) for item in detail)
    return str(detail)


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles: set[str] = {
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.WAREHOUSE_WORKER,
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not _has_any_role(request.user, self.allowed_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "products_count": Product.objects.count(),
                "warehouses_count": Warehouse.objects.count(),
                "stock_items_count": StockItem.objects.count(),
                "orders_count": Order.objects.count(),
                "recent_orders": Order.objects.select_related("customer", "created_by")[:5],
            }
        )
        return context


class ProductsPageView(RoleRequiredMixin, TemplateView):
    template_name = "products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "products": Product.objects.select_related("category").all(),
                "form": kwargs.get("form") or ProductCreateForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        if not _has_any_role(request.user, {UserRole.ADMIN, UserRole.MANAGER}):
            raise PermissionDenied
        form = ProductCreateForm(request.POST)
        if form.is_valid():
            product = form.save()
            log_action(request.user, AuditAction.CREATE, product)
            messages.success(request, "Product created.")
            return redirect("products-page")
        return self.render_to_response(self.get_context_data(form=form))


class StockPageView(RoleRequiredMixin, TemplateView):
    template_name = "stock.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_items"] = StockItem.objects.select_related("product", "warehouse").all()
        return context


class OrdersPageView(RoleRequiredMixin, TemplateView):
    template_name = "orders.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "orders": Order.objects.select_related("customer", "created_by").prefetch_related("items__product"),
                "form": kwargs.get("form") or OrderCreateForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        if not _has_any_role(request.user, {UserRole.ADMIN, UserRole.MANAGER}):
            raise PermissionDenied
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            try:
                create_order(
                    customer=form.cleaned_data["customer"],
                    items=[
                        {
                            "product": form.cleaned_data["product"],
                            "quantity": form.cleaned_data["quantity"],
                        }
                    ],
                    created_by=request.user,
                )
            except ValidationError as exc:
                form.add_error(None, _format_validation_error(exc))
            else:
                messages.success(request, "Order created.")
                return redirect("orders-page")
        return self.render_to_response(self.get_context_data(form=form))
