# Jinja Templates Overview

This project uses Jinja2 templates to render HTML on the server before sending it to the browser. FastAPI provides `Jinja2Templates`, which loads templates from a directory and renders them with a context dictionary.

## How Templates Are Loaded

In the routes layer, a `Jinja2Templates` instance is created with the templates directory:

```python
templates = Jinja2Templates(directory="templates")
```

When a request needs to render HTML, the handler returns a `TemplateResponse`:

```python
return templates.TemplateResponse(
    request,
    "home.html",
    {"request": request, "posts": posts, "title": ""},
)
```

- The first argument is the `Request` object (required by FastAPI for template rendering).
- The second argument is the template filename.
- The third argument is the template context, a dictionary of variables available in the template.

## Variable Interpolation

Jinja uses `{{ ... }}` to insert variables into HTML and `{% ... %}` for control flow (if, for, etc.).

### Example: `title`

In `home.html`:

```html
<title>
    {% if title %}
    Custom Blog - {{ title }}
    {% else %}
    Custom Blog - Home
    {% endif %}
</title>
```

- `title` comes from the context dictionary.
- If `title` is a non-empty string, it is rendered inside the page title.
- If `title` is empty or missing, the template renders a fallback string.

### Example: `posts`

In `home.html`:

```html
{% for post in posts %}
<h2>{{ post.title }}</h2>
<p>{{ post.content }}</p>
{% endfor %}
```

- `posts` is a list of objects (typically Pydantic schemas) passed to the template.
- The `{% for %}` loop iterates each item and exposes it as `post`.
- `post.title` and `post.content` are attributes rendered into the HTML.

## Notes and Best Practices

- Always pass the `request` key in the context so FastAPI can attach request data to the template.
- Treat template variables as read-only; any data shaping should happen in the route handler.
- Provide sensible defaults (like empty `title`) to keep templates predictable.
- Keep templates focused on presentation logic and avoid heavy business logic in Jinja.
