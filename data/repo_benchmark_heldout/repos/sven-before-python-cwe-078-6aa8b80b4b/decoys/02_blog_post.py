def get_list_context(context=None):
	list_context = frappe._dict(
		template = "templates/includes/blog/blog.html",
		get_list = get_blog_list,
		hide_filters = True,
		children = get_children(),
		# show_search = True,
		title = _('Blog')
	)

	category = sanitize_html(frappe.local.form_dict.blog_category or frappe.local.form_dict.category)
	if category:
		category_title = get_blog_category(category)
		list_context.sub_title = _("Posts filed under {0}").format(category_title)
		list_context.title = category_title

	elif frappe.local.form_dict.blogger:
		blogger = frappe.db.get_value("Blogger", {"name": frappe.local.form_dict.blogger}, "full_name")
		list_context.sub_title = _("Posts by {0}").format(blogger)
		list_context.title = blogger

	elif frappe.local.form_dict.txt:
		list_context.sub_title = _('Filtered by "{0}"').format(sanitize_html(frappe.local.form_dict.txt))

	if list_context.sub_title:
		list_context.parents = [{"name": _("Home"), "route": "/"},
								{"name": "Blog", "route": "/blog"}]
	else:
		list_context.parents = [{"name": _("Home"), "route": "/"}]

	list_context.update(frappe.get_doc("Blog Settings", "Blog Settings").as_dict(no_default_fields=True))
	return list_context
