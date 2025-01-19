import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from plyer import notification
from PIL import Image, ImageTk
import csv

# Global Variables
db_name = "expenses.db"
category_options = ["Food", "Travel", "Stationery", "Miscellaneous"]
budget = 5000  # Default budget


# Database Functions
def initialize_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_expense_to_db(category, amount, description):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (category, amount, description, timestamp)
        VALUES (?, ?, ?, ?)
    """, (category, amount, description, timestamp))
    conn.commit()
    conn.close()


def fetch_expenses_from_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses")
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_expense_from_db(expense_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def clear_all_expenses_from_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()


def update_expense_in_db(expense_id, category, amount, description):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE expenses
        SET category = ?, amount = ?, description = ?
        WHERE id = ?
    """, (category, amount, description, expense_id))
    conn.commit()
    conn.close()


# Tracker Functions
def add_expense():
    category = category_var.get()
    description = description_var.get().strip()
    amount = amount_var.get()

    if not category or not description:
        messagebox.showerror("Missing Data", "Please fill in all fields.")
        return

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
    except ValueError as e:
        messagebox.showerror("Invalid Input", str(e))
        return

    add_expense_to_db(category, amount, description)
    messagebox.showinfo("Success", "Expense added successfully!")
    category_var.set("")
    amount_var.set("")
    description_var.set("")
    load_table()
    check_budget()


def load_table():
    for row in table.get_children():
        table.delete(row)

    rows = fetch_expenses_from_db()
    for i, row in enumerate(rows, start=1):
        table.insert("", "end", values=(i, row[1], f"₹{row[2]:.2f}", row[3], row[4]))

    update_budget_tracker()


def analyze_expenses():
    rows = fetch_expenses_from_db()
    if not rows:
        messagebox.showinfo("No Data", "No expenses to analyze.")
        return

    total_spent = sum(row[2] for row in rows)
    category_summary = {}
    for row in rows:
        category_summary[row[1]] = category_summary.get(row[1], 0) + row[2]

    show_expense_plot(category_summary)


def show_expense_plot(category_summary):
    categories = list(category_summary.keys())
    amounts = list(category_summary.values())

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
    ax.axis('equal')
    ax.set_title("Expense Breakdown by Category")

    plot_window = tk.Toplevel(window)
    plot_window.title("Expense Visualization")

    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    plt.close(fig)


def check_budget():
    rows = fetch_expenses_from_db()
    total_spent = sum(row[2] for row in rows)
    remaining_budget = budget - total_spent

    if remaining_budget < 0:
        notification.notify(
            title="Budget Exceeded!",
            message=f"Budget exceeded by ₹{-remaining_budget:.2f}. Review your expenses.",
            timeout=10
        )
    elif total_spent / budget >= 0.8:
        notification.notify(
            title="Budget Alert!",
            message="You have spent 80% of your budget. Be cautious!",
            timeout=10
        )

    update_budget_tracker()


def update_budget_tracker():
    rows = fetch_expenses_from_db()
    total_spent = sum(row[2] for row in rows)
    remaining_budget = budget - total_spent
    budget_label.config(
        text=f"Budget: ₹{budget:.2f} | Spent: ₹{total_spent:.2f} | Remaining: ₹{remaining_budget:.2f}",
        fg="red" if remaining_budget < 0 else "green"
    )


def edit_expense():
    selected_item = table.selection()
    if not selected_item:
        messagebox.showerror("Select Expense", "Please select an expense to edit.")
        return

    selected_expense = table.item(selected_item)["values"]
    expense_id = selected_expense[0]

    category_var.set(selected_expense[1])
    amount_var.set(selected_expense[2].replace("₹", ""))
    description_var.set(selected_expense[3])

    def save_edits():
        new_category = category_var.get()
        new_amount = amount_var.get()
        new_description = description_var.get().strip()

        if not new_category or not new_description:
            messagebox.showerror("Missing Data", "Please fill in all fields.")
            return

        try:
            new_amount = float(new_amount)
            if new_amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        update_expense_in_db(expense_id, new_category, new_amount, new_description)
        messagebox.showinfo("Success", "Expense updated successfully!")
        load_table()
        check_budget()

    ttk.Button(input_frame, text="Save Edits", command=save_edits).grid(row=3, column=2, padx=10)


def tracker():
    global table, budget_label, category_var, amount_var, description_var, budget_entry, input_frame

    if hasattr(window, "tracker_window") and window.tracker_window.winfo_exists():
        window.tracker_window.deiconify()
        return

    tracker_window = tk.Toplevel(window)
    tracker_window.geometry("1000x750")
    tracker_window.title("Expense Tracker")
    window.tracker_window = tracker_window

    input_frame = tk.Frame(tracker_window, bg="#f0f0f0", pady=10)
    input_frame.pack(fill="x", padx=20, pady=10)

    tk.Label(input_frame, text="Category:", bg="#f0f0f0").grid(row=0, column=0, padx=10)
    category_var = tk.StringVar()
    ttk.Combobox(input_frame, textvariable=category_var, values=category_options).grid(row=0, column=1, padx=10)

    tk.Label(input_frame, text="Amount:", bg="#f0f0f0").grid(row=1, column=0, padx=10)
    amount_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=amount_var).grid(row=1, column=1, padx=10)

    tk.Label(input_frame, text="Description:", bg="#f0f0f0").grid(row=2, column=0, padx=10)
    description_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=description_var).grid(row=2, column=1, padx=10)

    ttk.Button(input_frame, text="Add Expense", command=add_expense).grid(row=3, column=0, padx=10)
    ttk.Button(input_frame, text="Edit Expense", command=edit_expense).grid(row=3, column=1, padx=10)

    budget_frame = tk.Frame(tracker_window, bg="#f0f0f0", pady=10)
    budget_frame.pack(fill="x", padx=20, pady=10)

    tk.Label(budget_frame, text="Set Budget (₹):", bg="#f0f0f0").grid(row=0, column=0, padx=10)
    budget_entry = tk.Entry(budget_frame)
    budget_entry.grid(row=0, column=1, padx=10)
    ttk.Button(budget_frame, text="Update Budget", command=lambda: add_expense_to_db(budget_entry.get())).grid(row=0, column=2, padx=10)

    budget_label = tk.Label(budget_frame, text="Budget: ₹0.00 | Spent: ₹0.00 | Remaining: ₹0.00", bg="#f0f0f0", fg="green")
    budget_label.grid(row=1, column=0, columnspan=3, pady=10)
    
    # Expense Table
    columns = ("sr_no", "category", "amount", "description", "timestamp")
    table_frame = tk.Frame(tracker_window)
    table_frame.pack(fill="both", expand=True, padx=20, pady=10)

    table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    for col in columns:
        table.heading(col, text=col.capitalize())
        table.column(col, anchor="center", width=150)
    table.grid(row=0, column=0, sticky="nsew")

    # Add scrollbars
    scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    scrollbar_y.grid(row=0, column=1, sticky="ns")
    table.configure(yscroll=scrollbar_y.set)

    scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
    scrollbar_x.grid(row=1, column=0, sticky="ew")
    table.configure(xscroll=scrollbar_x.set)

    ttk.Button(tracker_window, text="Analyze Expenses", command=analyze_expenses).pack(pady=10)
    ttk.Button(tracker_window, text="Clear All Expenses", command=clear_all_expenses_from_db).pack()

    load_table()
    check_budget()


# Main Application Window
window = tk.Tk()
window.title("SIT Expense Manager")
window.geometry("1000x700")

# Wait for window to be fully rendered before resizing the background image
window.update()

# Background for Welcome Page
bg_img = Image.open("background.png")
bg_img = bg_img.resize((window.winfo_width(), window.winfo_height()))
bg_img_tk = ImageTk.PhotoImage(bg_img)

bg_label = tk.Label(window, image=bg_img_tk)
bg_label.image = bg_img_tk  # Keep a reference to the image object
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

ttk.Button(window, text="Open Expense Tracker", command=tracker).pack(pady=10)

initialize_db()

window.mainloop()
