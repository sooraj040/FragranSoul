from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='Category', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=80, unique=True)), ('slug', models.SlugField(unique=True))]),
        migrations.CreateModel(name='Product', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=150)), ('slug', models.SlugField(unique=True)), ('brand', models.CharField(default='FragranSoul', max_length=100)), ('gender', models.CharField(choices=[('women','Women'),('men','Men'),('unisex','Unisex')], default='unisex', max_length=10)), ('description', models.TextField()), ('notes', models.CharField(blank=True, max_length=250)), ('price', models.DecimalField(decimal_places=2, max_digits=9)), ('old_price', models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)), ('image', models.ImageField(blank=True, null=True, upload_to='products/')), ('is_featured', models.BooleanField(default=False)), ('is_new', models.BooleanField(default=True)), ('stock', models.PositiveIntegerField(default=20)), ('created_at', models.DateTimeField(auto_now_add=True)), ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='store.category'))], options={'ordering':['-created_at']})
    ]
