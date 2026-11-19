from django import forms

from .models import AssetField, Holding

_FORM_FIELDS = {
    AssetField.FieldType.TEXT: lambda f: forms.CharField(max_length=500),
    AssetField.FieldType.NUMBER: lambda f: forms.DecimalField(),
    AssetField.FieldType.DATE: lambda f: forms.DateField(help_text="YYYY-MM-DD"),
    AssetField.FieldType.CHOICE: lambda f: forms.ChoiceField(choices=[("", "---------")] + [(o, o) for o in f.options]),
}


class HoldingAdminForm(forms.ModelForm):
    """Shows the holding's custom fields (its asset type's AssetFields, for
    its portfolio) as real inputs instead of raw JSON. They appear once the
    holding has been saved with a type; change the type and the old values
    are dropped, since they belonged to the old type's fields."""

    class Meta:
        model = Holding
        exclude = ["custom_fields"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_inputs = []  # (form field name, AssetField)
        holding = self.instance
        if holding.pk and holding.asset_type_id:
            for asset_field in holding.available_fields():
                name = f"custom__{asset_field.key}"
                form_field = _FORM_FIELDS[asset_field.field_type](asset_field)
                form_field.required = False
                form_field.label = asset_field.name
                form_field.initial = holding.custom_fields.get(asset_field.key)
                self.fields[name] = form_field
                self.custom_inputs.append((name, asset_field))

    def clean(self):
        cleaned = super().clean()
        type_changed = self.instance.pk and cleaned.get("asset_type") and (
            cleaned["asset_type"].pk != self.instance.asset_type_id
        )
        if type_changed:
            self.instance.custom_fields = {}
        else:
            self.instance.custom_fields = {
                asset_field.key: cleaned[name]
                for name, asset_field in self.custom_inputs
                if cleaned.get(name) not in (None, "")
            }
        return cleaned
