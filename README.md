# Flask-MongoDB Web App

- This is a web app that allows users to combine ingredients to create their own protein shakes.
- All CRUD operations are supported:
  - **C**: Users can create their recipe.
  - **R**: Users can read all recipes created.
  - **U**: Users can update a recipe.
  - **D**: Users can delete a recipe.
- There are two major features:
  1. Instead of using just a text input box, I implemented a step-by-step method for creating and editing recipes. This process utilizes the Flask session to preserve state across requests. This feature enhances the user experience by actively involving them in the creation and modification of their recipes.
  2. Sort buttons were added for viewing all recipes. Recipes are sorted in descending order by creation time by default, but users can also choose to sort by recipe name (both ascending and descending) or ascending by creation time.
