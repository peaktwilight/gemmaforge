        def view_grocery_list():
            print("grocery== list")
            groceryListFrame = Frame(self)
            groceryListFrame.rowconfigure(0, weight=1)
            groceryListFrame.columnconfigure(0, weight=1)
            groceryListFrame.rowconfigure(1, weight=3)
            groceryListFrame.columnconfigure(1, weight=3)
            groceryListFrame.pack()

            menu.pack_forget()
            groceryButton.pack_forget()
            label.configure(text="Grocery List")

            i = 0
            database_file = "meal_planner.db"
            item_array = []
            with sqlite3.connect(database_file) as conn:
                cursor = conn.cursor()
                tableName = "ingredients_" + str(weekNumber)
                selection = cursor.execute("""SELECT * FROM ?;""", (tableName, ))
                for result in [selection]:
                    for row in result.fetchall():
                        print(row)
                        for ingredient in row:
                            print(ingredient)
                            item_array.append(str(ingredient).split())
                        i = i +1
                        Label(groceryListFrame, text=ingredient, font=MEDIUM_FONT, justify=LEFT).grid(row=i, column=0, sticky="w")
            

            j = 0
            for item in item_array:
                print(item)


            returnButton = Button(menuFrame, text = "Return to Menu", highlightbackground="#e7e7e7", command=lambda: [groceryListFrame.pack_forget(),
                                                                                     menu.pack(), returnButton.pack_forget(), label.configure(text="Meal Planer"),
                                                                                    groceryButton.pack(side=RIGHT)])
            returnButton.pack(side=RIGHT)
