1. APPS
The "accounts" app contains a custom "User" model; a Django "AbstractUser" with optional "job_title" field; and the sign-up, sign-in, and sign-out views. This app also has three "Roles" that use built-in Django flags, which are customers (plain users), employee (is_staff), and admin (is_superuser).
The "products" app contains the catalog, which has "Category", "Tag", "Product", and a custom queryset. It also contains the pages for catalog, category, product-detail, and back-office. Finally, it houses the seed command to reset the "demo data".
The "orders" apps contains the models for Cart and CartItem, and Order and OrderItem; the views for cart and checkout; the order history of the customer; and the pages for "back-office" Checkout uses orders/services.py's "place_order".
The dashboard app is the analytics page exclusively for staff. It has the following aggregations in dashboard/queries.py: total revenue, order count, average order value, revenue over time, and top products.

2. PATH TRACE
Browser requests the home page, config/urls.py sends it to products/urls.py, which selects the correct pattern to send it to products/views.py, which then renders templates/products/catalog.html as an extension of templates/base.html, which finally sends the html back to the browser.

3. READ MODEL
The "User" model represents the different types of users capable of logging into the website: the customers, the employees, and the admins. I found it interesting that the "job_title" field deliberately specified it could be null or blank.

4. CATEGORY DELETION
If the category has products, it will throw a ProtectedError and remain untouched. Only categories that do not have any products can be deleted. The reason for this is because the Product class's foreign key has "on_delete=models.PROTECT".

5. TESTS
The suite is structured so each app contains its own tests. The conftest.py file contains shared test data for the other tests.

6. MY UNDERSTANDING
I'm still looking through the codebase. There is a lot I still don't understand, like how the pages access login information across pages for example. It will take my some time to understand it all. Claude does help, but not as much as I thought. I'm the type that needs to read code for myself to understand what it does.