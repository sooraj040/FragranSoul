"""Replace gender/product-level pricing with size-based perfume variants."""

from django.db import migrations, models
import django.db.models.deletion


def remove_demo_product_data(apps, schema_editor):
    """Do not carry old sample products into the new client-ready store."""
    Product = apps.get_model("store", "Product")
    Product.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("store", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("volume_ml", models.PositiveIntegerField(help_text="Enter the bottle size, e.g. 8, 10, 20 or 30.", verbose_name="Bottle size (ml)")),
                ("price", models.DecimalField(decimal_places=2, max_digits=9)),
                ("old_price", models.DecimalField(blank=True, decimal_places=2, help_text="Optional original price shown with a strikethrough.", max_digits=9, null=True)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="store.product")),
            ],
            options={
                "ordering": ["volume_ml"],
                "verbose_name": "Bottle Size / Variant",
                "verbose_name_plural": "Bottle Sizes / Variants",
            },
        ),
        migrations.RunPython(remove_demo_product_data, migrations.RunPython.noop),
        migrations.RemoveField(model_name="product", name="gender"),
        migrations.AlterField(
            model_name="product",
            name="notes",
            field=models.CharField(blank=True, help_text="Example: Bergamot, amber and vanilla.", max_length=250),
        ),
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["name"], "verbose_name_plural": "Categories"},
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["-created_at"], "verbose_name": "Perfume", "verbose_name_plural": "Perfumes"},
        ),
        migrations.RemoveField(model_name="product", name="price"),
        migrations.RemoveField(model_name="product", name="old_price"),
        migrations.RemoveField(model_name="product", name="stock"),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.UniqueConstraint(fields=("product", "volume_ml"), name="unique_product_volume"),
        ),
    ]
