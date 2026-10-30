
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date

app = Flask(__name__)
DB = "library.db"


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize():
    conn = connect()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS Books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        available INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS Members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        return_date TEXT,
        status TEXT DEFAULT 'Issued',
        FOREIGN KEY(book_id) REFERENCES Books(id),
        FOREIGN KEY(member_id) REFERENCES Members(id)
    );
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


# DASHBOARD
@app.route("/api/stats")
def stats():
    conn = connect()

    total = conn.execute(
        "SELECT COUNT(*) FROM Books"
    ).fetchone()[0]

    available = conn.execute(
        "SELECT COUNT(*) FROM Books WHERE available=1"
    ).fetchone()[0]

    issued = conn.execute(
        "SELECT COUNT(*) FROM Books WHERE available=0"
    ).fetchone()[0]

    members = conn.execute(
        "SELECT COUNT(*) FROM Members"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "total": total,
        "available": available,
        "issued": issued,
        "members": members
    })


# BOOKS: GET AND SEARCH
@app.route("/api/books", methods=["GET"])
def get_books():
    search = request.args.get("search", "")

    conn = connect()
    rows = conn.execute("""
        SELECT * FROM Books
        WHERE title LIKE ?
        OR author LIKE ?
        OR isbn LIKE ?
        OR category LIKE ?
        ORDER BY id DESC
    """, tuple([f"%{search}%"] * 4)).fetchall()

    conn.close()
    return jsonify([dict(row) for row in rows])


# ADD BOOK
@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    isbn = data.get("isbn", "").strip()
    category = data.get("category", "").strip()

    if not all([title, author, isbn, category]):
        return jsonify({"error": "All fields are required"}), 400

    conn = connect()

    try:
        conn.execute("""
            INSERT INTO Books(title, author, isbn, category)
            VALUES (?, ?, ?, ?)
        """, (title, author, isbn, category))

        conn.commit()
        return jsonify({"message": "Book added successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "ISBN already exists"}), 409

    finally:
        conn.close()


# UPDATE BOOK
@app.route("/api/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}

    fields = [
        data.get("title", "").strip(),
        data.get("author", "").strip(),
        data.get("isbn", "").strip(),
        data.get("category", "").strip()
    ]

    if not all(fields):
        return jsonify({"error": "All fields are required"}), 400

    conn = connect()

    try:
        cursor = conn.execute("""
            UPDATE Books
            SET title=?, author=?, isbn=?, category=?
            WHERE id=?
        """, (*fields, book_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404

        conn.commit()
        return jsonify({"message": "Book updated successfully"})

    except sqlite3.IntegrityError:
        return jsonify({"error": "ISBN already exists"}), 409

    finally:
        conn.close()


# DELETE BOOK
@app.route("/api/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    conn = connect()

    try:
        cursor = conn.execute(
            "DELETE FROM Books WHERE id=?", (book_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404

        conn.commit()
        return jsonify({"message": "Book deleted successfully"})

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Cannot delete a book with transaction history"
        }), 409

    finally:
        conn.close()


# MEMBERS: GET
@app.route("/api/members", methods=["GET"])
def get_members():
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM Members ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


# ADD MEMBER
@app.route("/api/members", methods=["POST"])
def add_member():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()

    if not all([name, email, phone]):
        return jsonify({"error": "All fields are required"}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Invalid email address"}), 400

    conn = connect()

    try:
        conn.execute("""
            INSERT INTO Members(name, email, phone)
            VALUES (?, ?, ?)
        """, (name, email, phone))

        conn.commit()
        return jsonify({"message": "Member added successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 409

    finally:
        conn.close()


# DELETE MEMBER
@app.route("/api/members/<int:member_id>", methods=["DELETE"])
def delete_member(member_id):
    conn = connect()

    try:
        cursor = conn.execute(
            "DELETE FROM Members WHERE id=?", (member_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404

        conn.commit()
        return jsonify({"message": "Member deleted successfully"})

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Cannot delete a member with transaction history"
        }), 409

    finally:
        conn.close()


# ISSUE BOOK
@app.route("/api/issue", methods=["POST"])
def issue_book():
    data = request.get_json(silent=True) or {}

    book_id = data.get("book_id")
    member_id = data.get("member_id")

    if not book_id or not member_id:
        return jsonify({"error": "Select a book and member"}), 400

    conn = connect()

    try:
        conn.execute("BEGIN IMMEDIATE")

        book = conn.execute(
            "SELECT * FROM Books WHERE id=?", (book_id,)
        ).fetchone()

        member = conn.execute(
            "SELECT * FROM Members WHERE id=?", (member_id,)
        ).fetchone()

        if not book:
            return jsonify({"error": "Book not found"}), 404

        if not member:
            return jsonify({"error": "Member not found"}), 404

        if book["available"] == 0:
            return jsonify({"error": "Book is already issued"}), 409

        conn.execute("""
            INSERT INTO Transactions(book_id, member_id, issue_date)
            VALUES (?, ?, ?)
        """, (book_id, member_id, date.today().isoformat()))

        conn.execute(
            "UPDATE Books SET available=0 WHERE id=?", (book_id,)
        )

        conn.commit()
        return jsonify({"message": "Book issued successfully"}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


# VIEW TRANSACTIONS
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    conn = connect()

    rows = conn.execute("""
        SELECT Transactions.*,
               Books.title AS book_title,
               Members.name AS member_name
        FROM Transactions
        JOIN Books ON Transactions.book_id=Books.id
        JOIN Members ON Transactions.member_id=Members.id
        ORDER BY Transactions.id DESC
    """).fetchall()

    conn.close()
    return jsonify([dict(row) for row in rows])


# RETURN BOOK
@app.route("/api/return/<int:transaction_id>", methods=["PUT"])
def return_book(transaction_id):
    conn = connect()

    try:
        conn.execute("BEGIN IMMEDIATE")

        transaction = conn.execute("""
            SELECT * FROM Transactions
            WHERE id=?
        """, (transaction_id,)).fetchone()

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        if transaction["status"] == "Returned":
            return jsonify({"error": "Book already returned"}), 409

        conn.execute("""
            UPDATE Transactions
            SET status='Returned', return_date=?
            WHERE id=?
        """, (date.today().isoformat(), transaction_id))

        conn.execute("""
            UPDATE Books SET available=1 WHERE id=?
        """, (transaction["book_id"],))

        conn.commit()
        return jsonify({"message": "Book returned successfully"})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


if __name__ == "__main__":
    initialize()
    app.run(debug=True)
