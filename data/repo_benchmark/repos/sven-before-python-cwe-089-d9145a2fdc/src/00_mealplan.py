        def callback(recipeName):
            menu.pack_forget()
            viewRecipeFrame.pack(expand=True, fill='both')
            groceryButton.pack_forget()
            database_file = "meal_planner.db"
            print(recipeName)
            with sqlite3.connect(database_file) as conn:
                cursor = conn.cursor()
                selection = cursor.execute("""SELECT * FROM recipe WHERE name = """ + "\"" + recipeName + "\"")
                for result in [selection]:
                    for row in result.fetchall():
                        name = row[0]
                        time = row[1]
                        servings = row[2]
                        ingredients = row[4]
                        directions = row[5]

                        string = ("Name: {} \n Cook time: {} \n Number of Servings: {} \n ".format(name, time, servings))
                        secondString = ("Ingredients: {}".format(ingredients))
                        thirdString = ("Directions: {}".format(directions))
            Label(viewRecipeFrame, text=string, font=MEDIUM_FONT, bg="#f8f8f8", fg="#000000").pack(side=TOP)
            Label(viewRecipeFrame, text=secondString, font=MEDIUM_FONT, bg="#f8f8f8", fg="#000000").pack(side=TOP)
            Label(viewRecipeFrame, text=thirdString, font=MEDIUM_FONT, bg="#f8f8f8", fg="#000000").pack(side=TOP)
            returnButton = Button(menuFrame, text = "Return to Menu", highlightbackground="#e7e7e7", command=lambda: [viewRecipeFrame.pack_forget(),
                                                                                     menu.pack(), returnButton.pack_forget(), label.configure(text="Meal Planer"),
                                                                                    groceryButton.pack(side=RIGHT)])
            returnButton.pack(side=RIGHT)
