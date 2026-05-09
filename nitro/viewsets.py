"""
Nitro 0.8 - CRUD ViewSet Factory.

Generates Create/Update/Delete view triplets for models with standard
HTMX slideover + toast patterns, eliminating repetitive boilerplate.

Usage:
    from nitro.viewsets import nitro_crud_viewset
    from core.mixins import CompanyMixin

    RecurringChargeCreateView, RecurringChargeUpdateView, RecurringChargeDeleteView = \\
        nitro_crud_viewset(
            model=RecurringCharge,
            form_class=RecurringChargeForm,
            app_name='leasing',
            prefix='recurring-charge',
        )

    # With customization:
    views = nitro_crud_viewset(
        model=BuyerContact,
        form_class=BuyerContactForm,
        app_name='construction',
        prefix='buyer-contact',
        success_messages={'create': 'Contacto agregado', 'update': 'Contacto actualizado'},
        parent_field='buyer',          # obj.company = obj.buyer.company
        mixins=[CompanyMixin],         # Additional mixins (CompanyMixin is always included)
        pass_company_to_form=True,     # Pass company kwarg to form
        assign_company=True,           # Set obj.company on create
    )
"""

from nitro.views import NitroCreateView, NitroUpdateView, NitroDeleteView


def nitro_crud_viewset(model, form_class, app_name, prefix,
                       success_messages=None, parent_field=None,
                       mixins=None, pass_company_to_form=True,
                       assign_company=True, can_delete=None,
                       redirect_url=None, soft_delete=False):
    """
    Generate Create, Update, Delete views for a model.

    Args:
        model: Django model class
        form_class: Form class for create/update
        app_name: App name for template paths (e.g. 'leasing')
        prefix: URL/template prefix (e.g. 'recurring-charge')
        success_messages: Dict with 'create', 'update', 'delete' messages
        parent_field: Field name to inherit company from (e.g. 'lease')
        mixins: Additional mixin classes (list)
        pass_company_to_form: Pass company to form kwargs
        assign_company: Assign company to obj on create
        can_delete: Callable(obj) -> (bool, error_msg) for delete validation
        redirect_url: URL to redirect after delete
        soft_delete: Use soft delete (is_active=False) instead of hard delete

    Returns:
        Tuple of (CreateView, UpdateView, DeleteView)
    """
    if success_messages is None:
        success_messages = {}

    model_name = model.__name__
    template = f'{app_name}/partials/{prefix.replace("-", "_")}_form.html'

    # Build base classes list
    base_mixins = list(mixins or [])

    # --- CreateView ---
    create_attrs = {
        'model': model,
        'form_class': form_class,
        'template_name': template,
        'slideover_id': f'create-{prefix}',
        'success_message': success_messages.get('create'),
        'pass_company_to_form': pass_company_to_form,
        'assign_company': assign_company,
    }

    if parent_field:
        def _save_object_create(self, obj, form):
            if not obj.company_id and hasattr(obj, parent_field):
                parent = getattr(obj, parent_field, None)
                if parent and hasattr(parent, 'company'):
                    obj.company = parent.company
            obj.save()
        create_attrs['save_object'] = _save_object_create

    CreateView = type(
        f'{model_name}CreateView',
        tuple(base_mixins + [NitroCreateView]),
        create_attrs,
    )

    # --- UpdateView ---
    update_attrs = {
        'model': model,
        'form_class': form_class,
        'template_name': template,
        'slideover_id': f'edit-{prefix}',
        'success_message': success_messages.get('update'),
        'pass_company_to_form': pass_company_to_form,
    }

    UpdateView = type(
        f'{model_name}UpdateView',
        tuple(base_mixins + [NitroUpdateView]),
        update_attrs,
    )

    # --- DeleteView ---
    delete_attrs = {
        'model': model,
        'success_message': success_messages.get('delete'),
        'redirect_url': redirect_url,
        'soft_delete': soft_delete,
    }

    if can_delete:
        delete_attrs['can_delete'] = can_delete

    DeleteView = type(
        f'{model_name}DeleteView',
        tuple(base_mixins + [NitroDeleteView]),
        delete_attrs,
    )

    return CreateView, UpdateView, DeleteView
