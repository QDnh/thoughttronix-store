## Featured Products
Question 1: - Trace the feature. Explain how marking a product as featured in the admin interface causes the badge to appear in the storefront. Explain the files involved and the code logic. 

Q1 Answer: Claude modified products/models.py, templates/products/catalog.html, and templates/products/detail.html. When looping to display products, the templates check for if the is_featured value of the Product model is true or false, and displays the badge on the product if the value is true. 

Question 2 - How you verified it. Describe how you confirmed the feature works. Name the pages you checked in the browser.

Q2 Answer: I read the suggested code in real time before saying yes to Claude. In the browser, I checked the Catalog, products/seraphine/, products/soulsear-mark-i/, products/soulsear-mark-ii/ pages to make sure the badge was visible. I also looked at other product pages to check that the badge didn't always appear.

Question 3 - Judgement. Describe one challenge, unexpected result, or edge case you encountered. Explain what you did to troubleshoot it.

Q3 Answer: Claude tried to run makemigrations, migrations, and tests at the same time. I originally said yes, but realized I actually wanted to have Claude do each step one at a time. I cancelled the process and rewound to the previous state. I then ran the command again, but had Claude work step by step instead.