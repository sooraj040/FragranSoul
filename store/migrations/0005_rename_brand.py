from django.db import migrations


def rename_brand(apps, schema_editor):
    # Perfumes saved before the rename still carry the old brand spelling.
    Product = apps.get_model('store', 'Product')
    Product.objects.filter(brand='FraagranSoul').update(brand='FragranSoul')


class Migration(migrations.Migration):
    dependencies = [('store', '0004_product_gender')]
    operations = [migrations.RunPython(rename_brand, migrations.RunPython.noop)]
