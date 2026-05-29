from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0010_client_predio_registry_number'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['name'], name='pos_category_name_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['name'], name='pos_product_name_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(
                fields=['category', 'name'],
                name='pos_product_cat_name_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='promotionsdetail',
            index=models.Index(
                fields=['product', 'promotion'],
                name='pos_promodetail_prod_prom_idx',
            ),
        ),
    ]
