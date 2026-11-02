"""Helper for migration 0009: the Style links that migration 0003 created."""


def seeded_style_links():
    import importlib
    m = importlib.import_module('shop.migrations.0003_dynamic_catalogue')
    return {(label, link_label, link_url) for label, _url, _f, groups in m.DEFAULT_MENU for link_label, link_url in groups.get('Style', [])}
