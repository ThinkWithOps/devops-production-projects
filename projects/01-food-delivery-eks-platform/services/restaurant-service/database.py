import aiosqlite
import os

DATABASE_URL = os.getenv("DATABASE_URL", "restaurants.db")


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine_type TEXT NOT NULL,
                address TEXT NOT NULL,
                rating REAL DEFAULT 4.0,
                delivery_time_min INTEGER DEFAULT 30,
                min_order_amount REAL DEFAULT 10.0,
                is_open INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
            )
        """)
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM restaurants")
        count = (await cursor.fetchone())[0]
        if count == 0:
            restaurants = [
                ("The Golden Spice", "Indian", "245 Curry Lane, Manhattan, NY 10001", 4.7, 35, 15.0),
                ("Mama Rosa's Kitchen", "Italian", "88 Pasta Boulevard, Brooklyn, NY 11201", 4.5, 40, 12.0),
                ("Dragon Palace", "Chinese", "17 Jade Street, Queens, NY 11374", 4.3, 25, 10.0),
                ("El Taco Loco", "Mexican", "56 Fiesta Avenue, Bronx, NY 10451", 4.6, 20, 8.0),
                ("Sakura Sushi Bar", "Japanese", "123 Cherry Blossom Way, Manhattan, NY 10016", 4.8, 45, 20.0),
            ]
            cursor = await db.executemany(
                "INSERT INTO restaurants (name, cuisine_type, address, rating, delivery_time_min, min_order_amount) VALUES (?, ?, ?, ?, ?, ?)",
                restaurants,
            )
            await db.commit()

            menu_items = [
                # The Golden Spice (id=1) - Indian
                (1, "Butter Chicken", "Tender chicken in rich tomato-cream sauce with aromatic spices", 16.99, "Main Course"),
                (1, "Lamb Biryani", "Fragrant basmati rice layered with spiced slow-cooked lamb", 18.99, "Main Course"),
                (1, "Palak Paneer", "Fresh cottage cheese cubes in creamy spinach gravy", 14.99, "Vegetarian"),
                (1, "Garlic Naan", "Soft leavened bread brushed with garlic butter", 3.99, "Bread"),
                (1, "Chicken Tikka Masala", "Grilled chicken in spiced tomato and onion gravy", 17.99, "Main Course"),
                (1, "Mango Lassi", "Chilled yogurt drink blended with Alphonso mango pulp", 5.99, "Beverages"),
                (1, "Samosa (2 pcs)", "Crispy pastry filled with spiced potatoes and green peas", 6.99, "Appetizers"),
                (1, "Dal Makhani", "Slow-cooked black lentils in buttery tomato sauce", 13.99, "Vegetarian"),
                (1, "Chicken Korma", "Mild and creamy chicken curry with cashew nut sauce", 17.49, "Main Course"),
                (1, "Gulab Jamun", "Soft milk dumplings soaked in rose-flavored sugar syrup", 5.49, "Desserts"),
                # Mama Rosa's Kitchen (id=2) - Italian
                (2, "Spaghetti Carbonara", "Al dente pasta with pancetta, eggs, and Pecorino Romano", 17.99, "Pasta"),
                (2, "Margherita Pizza", "Classic Neapolitan pizza with San Marzano tomatoes and fresh mozzarella", 15.99, "Pizza"),
                (2, "Chicken Parmigiana", "Breaded chicken breast with marinara sauce and melted provolone", 19.99, "Main Course"),
                (2, "Fettuccine Alfredo", "Ribbons of pasta in silky Parmesan cream sauce", 16.99, "Pasta"),
                (2, "Bruschetta al Pomodoro", "Toasted sourdough with heirloom tomatoes and fresh basil", 8.99, "Appetizers"),
                (2, "Tiramisu", "Classic Italian dessert with espresso-soaked ladyfingers and mascarpone", 7.99, "Desserts"),
                (2, "Penne Arrabbiata", "Penne pasta in spicy tomato sauce with garlic and red chilies", 14.99, "Pasta"),
                (2, "Minestrone Soup", "Hearty vegetable soup with cannellini beans and pasta", 9.99, "Soups"),
                (2, "Osso Buco", "Braised veal shanks with gremolata on saffron risotto", 28.99, "Main Course"),
                (2, "Cannoli Siciliani", "Crispy pastry shells filled with sweet ricotta and chocolate chips", 6.99, "Desserts"),
                # Dragon Palace (id=3) - Chinese
                (3, "Kung Pao Chicken", "Diced chicken stir-fried with peanuts, dried chilies, and vegetables", 14.99, "Main Course"),
                (3, "Dim Sum Basket (6 pcs)", "Assorted steamed dumplings with shrimp, pork, and vegetables", 11.99, "Appetizers"),
                (3, "Beef and Broccoli", "Tender beef slices in savory oyster sauce with fresh broccoli", 15.99, "Main Course"),
                (3, "Mapo Tofu", "Silken tofu in spicy Sichuan bean paste sauce with ground pork", 13.99, "Main Course"),
                (3, "Spring Rolls (4 pcs)", "Crispy rolls filled with seasoned vegetables and glass noodles", 7.99, "Appetizers"),
                (3, "Sweet and Sour Pork", "Crispy pork pieces in vibrant sweet and sour glaze with peppers", 14.49, "Main Course"),
                (3, "Hot and Sour Soup", "Spicy and tangy soup with tofu, bamboo shoots, and mushrooms", 6.99, "Soups"),
                (3, "Yangzhou Fried Rice", "Wok-fried rice with shrimp, ham, eggs, and spring onions", 12.99, "Rice"),
                (3, "Peking Duck (half)", "Crispy roasted duck with pancakes, hoisin sauce, and scallions", 29.99, "Specialty"),
                (3, "Mango Pudding", "Chilled mango dessert with evaporated milk and mango pieces", 5.99, "Desserts"),
                # El Taco Loco (id=4) - Mexican
                (4, "Carne Asada Tacos (3 pcs)", "Grilled marinated skirt steak with salsa verde and cotija cheese", 13.99, "Tacos"),
                (4, "Chicken Burrito", "Flour tortilla with seasoned chicken, rice, black beans, and guacamole", 12.99, "Burritos"),
                (4, "Loaded Nachos", "Tortilla chips with queso, jalapeños, pico de gallo, and sour cream", 10.99, "Appetizers"),
                (4, "Shrimp Quesadilla", "Flour tortilla with sautéed shrimp, pepper jack cheese, and chipotle sauce", 13.49, "Quesadillas"),
                (4, "Al Pastor Tacos (3 pcs)", "Marinated pork with pineapple, cilantro, and onion on corn tortillas", 12.99, "Tacos"),
                (4, "Guacamole and Chips", "Freshly smashed avocado with lime, jalapeño, and house tortilla chips", 7.99, "Appetizers"),
                (4, "Beef Enchiladas (2 pcs)", "Corn tortillas filled with seasoned beef and smothered in red mole sauce", 14.99, "Main Course"),
                (4, "Horchata", "Cold cinnamon rice milk sweetened with vanilla", 3.99, "Beverages"),
                (4, "Churros with Chocolate", "Fried dough sticks dusted with cinnamon sugar and dark chocolate dip", 6.99, "Desserts"),
                (4, "Pozole Rojo", "Traditional hominy soup with pork, dried chilies, and garnishes", 11.99, "Soups"),
                # Sakura Sushi Bar (id=5) - Japanese
                (5, "Dragon Roll (8 pcs)", "Shrimp tempura and cucumber topped with avocado and eel sauce", 16.99, "Rolls"),
                (5, "Salmon Sashimi (8 pcs)", "Premium Atlantic salmon sliced thick and served with wasabi", 18.99, "Sashimi"),
                (5, "Tonkotsu Ramen", "Rich pork bone broth with chashu, soft egg, and bamboo shoots", 15.99, "Ramen"),
                (5, "Spicy Tuna Roll (8 pcs)", "Tuna with sriracha mayo, cucumber, and sesame seeds", 13.99, "Rolls"),
                (5, "Chicken Katsu Curry", "Crispy panko-breaded chicken with Japanese golden curry on steamed rice", 17.99, "Main Course"),
                (5, "Edamame", "Steamed salted young soybeans", 5.99, "Appetizers"),
                (5, "Gyoza (6 pcs)", "Pan-fried pork and cabbage dumplings with ponzu dipping sauce", 8.99, "Appetizers"),
                (5, "Rainbow Roll (8 pcs)", "California roll topped with assorted sashimi and avocado", 19.99, "Rolls"),
                (5, "Miso Soup", "Traditional dashi broth with tofu, wakame, and spring onions", 3.99, "Soups"),
                (5, "Matcha Ice Cream", "Premium ceremonial matcha flavored ice cream", 6.49, "Desserts"),
            ]
            await db.executemany(
                "INSERT INTO menu_items (restaurant_id, name, description, price, category) VALUES (?, ?, ?, ?, ?)",
                menu_items,
            )
            await db.commit()
