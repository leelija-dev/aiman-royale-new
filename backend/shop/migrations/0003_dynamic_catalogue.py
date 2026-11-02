from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify

DEFAULT_OCCASIONS = ['Haldi', 'Wedding', 'Party', 'Festive']
DEFAULT_COLOURS = [('Maroon', '#6b1426'), ('Rani Pink', '#d6246e'), ('Rose Gold', '#c9877d'), ('Copper', '#b8642f'),
                   ('Wine', '#5c0f2e'), ('Purple', '#4b2a7a'), ('Green', '#3f6b4a'), ('Navy', '#24315e'),
                   ('Red', '#b3202a'), ('Pink', '#e48aa6'), ('Beige', '#d9c4a5'), ('White', '#f4f1ea'), ('Black', '#1f1a18')]
STYLES = [('Anarkali Suits', 'anarkali-suits'), ('Kurta Sets', 'kurta-sets'), ('Palazzo Suits', 'palazzo-suits'), ('Sharara Suits', 'sharara-suits'),
          ('Patiala Suits', 'patiala-suits'), ('Jump Suits', 'jump-suits'), ('Kaftan', 'kaftan'), ('Indo Western', 'indo-western'),
          ('Co-ord Sets', 'co-ord-sets'), ('Crop Top Styles', 'crop-top-styles')]
SALWAR = [(label, f'/collections/{slug}') for label, slug in STYLES]
DEFAULT_MENU = [
    ('Wedding', '/collections/wedding', 'The Wedding Edit', {
        'Style': [('Wedding Lehengas', '/collections/lehengas?occasion=wedding'), ('Anarkali Suits', '/collections/anarkali-suits?occasion=wedding'),
                  ('Sharara Suits', '/collections/sharara-suits?occasion=wedding'), ('Palazzo Suits', '/collections/palazzo-suits?occasion=wedding'),
                  ('Gowns', '/collections/gown?occasion=wedding'), ('Indo Western', '/collections/indo-western?occasion=wedding')],
        'Collection': [('New Arrivals', '/collections/wedding?sort=newest'), ('Bridal Edit', '/collections/bridal'), ('Shop All Wedding', '/collections/wedding')]}),
    ('Bridal', '/collections/bridal', 'Bridal Couture', {
        'Style': [('Bridal Lehengas', '/collections/lehengas?occasion=wedding'), ('Bridal Gowns', '/collections/gown?occasion=wedding'),
                  ('Bridal Sharara', '/collections/sharara-suits?occasion=wedding'), ('Bridal Anarkali', '/collections/anarkali-suits?occasion=wedding')],
        'Collection': [('New Arrivals', '/collections/bridal?sort=newest'), ('Book a Bridal Fitting', '/appointment'), ('Shop All Bridal', '/collections/bridal')]}),
    ('Gown', '/collections/gown', 'Evening Gowns', {
        'Style': [('Anarkali Gowns', '/collections/gown?q=anarkali'), ('Indo Western Gowns', '/collections/indo-western'), ('Kaftan Gowns', '/collections/kaftan')],
        'Collection': [('New Arrivals', '/collections/gown?sort=newest'), ('Shop All Gowns', '/collections/gown')]}),
    ('Salwar Kameez', '/collections/salwar-kameez', 'Salwar Kameez', {
        'Style': SALWAR,
        'Collection': [('New Arrivals', '/collections/salwar-kameez?sort=newest'), ('Price: Low to High', '/collections/salwar-kameez?sort=price-asc'),
                       ('Shop All Salwar Kameez', '/collections/salwar-kameez')]}),
    ('Collections', '/products', 'All Collections', {
        'Style': SALWAR,
        'Collection': [('Wedding', '/collections/wedding'), ('Bridal', '/collections/bridal'), ('Gown', '/collections/gown'),
                       ('Salwar Kameez', '/collections/salwar-kameez'), ('Lehengas', '/collections/lehengas'),
                       ('New Arrivals', '/products?sort=newest'), ('View All', '/products')]}),
]


def forwards(apps, schema_editor):
    Occasion = apps.get_model('shop', 'Occasion')
    Colour = apps.get_model('shop', 'Colour')
    Product = apps.get_model('shop', 'Product')
    MenuItem = apps.get_model('shop', 'MenuItem')
    MenuLink = apps.get_model('shop', 'MenuLink')

    def occasion(name):
        name = name.strip()
        found = Occasion.objects.filter(name__iexact=name).first()
        if found:
            return found
        return Occasion.objects.create(name=name, slug=slugify(name) or f'occasion-{Occasion.objects.count() + 1}',
                                       sort_order=Occasion.objects.count() * 10)

    for name in DEFAULT_OCCASIONS:
        occasion(name)
    # Move each product's old text list of occasions into links to the new table.
    for p in Product.objects.all():
        for name in (p.occasions or []):
            if isinstance(name, str) and name.strip():
                p.occasion_links.add(occasion(name))
    for i, (name, hex_) in enumerate(DEFAULT_COLOURS):
        Colour.objects.get_or_create(name=name, defaults={'hex': hex_, 'sort_order': i * 10})
    if not MenuItem.objects.exists():
        for i, (label, url, feature, groups) in enumerate(DEFAULT_MENU):
            item = MenuItem.objects.create(label=label, url=url, sort_order=i * 10, feature_title=feature, feature_url=url)
            n = 0
            for group, links in groups.items():
                for link_label, link_url in links:
                    MenuLink.objects.create(item=item, group=group, label=link_label, url=link_url, sort_order=n)
                    n += 10


def backwards(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    for p in Product.objects.all():
        p.occasions = [o.name for o in p.occasion_links.all()]
        p.save(update_fields=['occasions'])


class Migration(migrations.Migration):
    dependencies = [('shop', '0002_order_payment_session_id_alter_order_payment_method')]

    operations = [
        migrations.CreateModel(name='Occasion', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=60, unique=True)),
            ('slug', models.SlugField(unique=True)),
            ('image', models.ImageField(blank=True, help_text='Card image for "Shop by Occasion".', upload_to='occasions/')),
            ('sort_order', models.PositiveIntegerField(default=0)),
            ('active', models.BooleanField(default=True)),
        ], options={'ordering': ['sort_order', 'name']}),
        migrations.CreateModel(name='Colour', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=40, unique=True)),
            ('hex', models.CharField(default='#999999', help_text='e.g. #6b1426', max_length=7, verbose_name='Swatch colour')),
            ('sort_order', models.PositiveIntegerField(default=0)),
        ], options={'ordering': ['sort_order', 'name']}),
        migrations.CreateModel(name='MenuItem', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('label', models.CharField(max_length=40)),
            ('url', models.CharField(help_text='e.g. /collections/salwar-kameez', max_length=200)),
            ('sort_order', models.PositiveIntegerField(default=0)),
            ('active', models.BooleanField(default=True)),
            ('show_occasions', models.BooleanField(default=True, help_text='Add an "Occasion" tab listing every active occasion automatically.')),
            ('feature_title', models.CharField(blank=True, max_length=60)),
            ('feature_image', models.ImageField(blank=True, upload_to='menu/')),
            ('feature_url', models.CharField(blank=True, max_length=200)),
        ], options={'ordering': ['sort_order', 'id']}),
        migrations.CreateModel(name='MenuLink', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('group', models.CharField(choices=[('Style', 'Style'), ('Occasion', 'Occasion'), ('Collection', 'Collection')], default='Style', max_length=20)),
            ('label', models.CharField(max_length=60)),
            ('url', models.CharField(max_length=200)),
            ('sort_order', models.PositiveIntegerField(default=0)),
            ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='shop.menuitem')),
        ], options={'ordering': ['sort_order', 'id']}),
        migrations.AddField(model_name='product', name='occasion_links',
                            field=models.ManyToManyField(blank=True, related_name='products', to='shop.occasion')),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name='product', name='occasions'),
        migrations.RenameField(model_name='product', old_name='occasion_links', new_name='occasions'),
    ]
