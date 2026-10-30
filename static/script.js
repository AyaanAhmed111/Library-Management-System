
const API = "/api";

async function api(url, method = "GET", data = null) {
    const options = { method };

    if (data !== null) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(data);
    }

    const response = await fetch(API + url, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "Something went wrong");
    }

    return result;
}

function toast(message) {
    const box = document.getElementById("toast");
    box.textContent = message;
    box.style.display = "block";

    setTimeout(() => {
        box.style.display = "none";
    }, 2500);
}

function showPage(page, button = null) {
    document.querySelectorAll(".page").forEach(p => {
        p.classList.add("hidden");
    });

    document.getElementById(page).classList.remove("hidden");

    document.getElementById("pageTitle").textContent =
        page === "issue" ? "Issue / Return" :
        page.charAt(0).toUpperCase() + page.slice(1);

    document.querySelectorAll(".nav").forEach(n => {
        n.classList.remove("active");
    });

    if (button) button.classList.add("active");

    if (page === "dashboard") loadDashboard();
    if (page === "books") loadBooks();
    if (page === "members") loadMembers();
    if (page === "issue") loadIssuePage();
}

async function loadDashboard() {
    try {
        const s = await api("/stats");

        document.getElementById("totalBooks").textContent = s.total;
        document.getElementById("availableBooks").textContent = s.available;
        document.getElementById("issuedBooks").textContent = s.issued;
        document.getElementById("totalMembers").textContent = s.members;

        const books = await api("/books");

        document.getElementById("recentBooks").innerHTML =
            books.slice(0, 5).map(b => `
                <tr>
                    <td>${escapeHTML(b.title)}</td>
                    <td>${escapeHTML(b.author)}</td>
                    <td>${escapeHTML(b.isbn)}</td>
                    <td>${escapeHTML(b.category)}</td>
                    <td>${statusBadge(b.available)}</td>
                </tr>
            `).join("") || emptyRow(5);
    } catch (e) {
        toast(e.message);
    }
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function statusBadge(available) {
    return available
        ? '<span class="status available">Available</span>'
        : '<span class="status issued">Issued</span>';
}

function emptyRow(columns) {
    return `<tr><td colspan="${columns}" style="text-align:center">No records found</td></tr>`;
}

// BOOKS

async function loadBooks() {
    try {
        const search = document.getElementById("bookSearch").value;
        const books = await api("/books?search=" + encodeURIComponent(search));

        document.getElementById("bookTable").innerHTML =
            books.map(b => `
                <tr>
                    <td>${b.id}</td>
                    <td>${escapeHTML(b.title)}</td>
                    <td>${escapeHTML(b.author)}</td>
                    <td>${escapeHTML(b.isbn)}</td>
                    <td>${escapeHTML(b.category)}</td>
                    <td>${statusBadge(b.available)}</td>
                    <td>
                        <button class="secondary" onclick="editBook(${b.id})">Edit</button>
                        <button class="danger" onclick="deleteBook(${b.id})">Delete</button>
                    </td>
                </tr>
            `).join("") || emptyRow(7);
    } catch (e) {
        toast(e.message);
    }
}

function openBookForm() {
    document.getElementById("bookForm").classList.remove("hidden");
    document.getElementById("bookFormTitle").textContent = "Add New Book";
    document.getElementById("bookId").value = "";
    ["title", "author", "isbn", "category"].forEach(id => {
        document.getElementById(id).value = "";
    });
}

function closeBookForm() {
    document.getElementById("bookForm").classList.add("hidden");
}

async function saveBook() {
    const id = document.getElementById("bookId").value;

    const data = {
        title: document.getElementById("title").value.trim(),
        author: document.getElementById("author").value.trim(),
        isbn: document.getElementById("isbn").value.trim(),
        category: document.getElementById("category").value.trim()
    };

    if (Object.values(data).some(v => !v)) {
        return toast("Please fill all fields");
    }

    try {
        await api("/books" + (id ? "/" + id : ""), id ? "PUT" : "POST", data);
        toast(id ? "Book updated successfully" : "Book added successfully");
        closeBookForm();
        await loadBooks();
        await loadDashboard();
    } catch (e) {
        toast(e.message);
    }
}

async function editBook(id) {
    try {
        const books = await api("/books");
        const book = books.find(b => b.id === id);

        if (!book) return toast("Book not found");

        document.getElementById("bookForm").classList.remove("hidden");
        document.getElementById("bookFormTitle").textContent = "Edit Book";
        document.getElementById("bookId").value = book.id;

        document.getElementById("title").value = book.title;
        document.getElementById("author").value = book.author;
        document.getElementById("isbn").value = book.isbn;
        document.getElementById("category").value = book.category;

        window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
        toast(e.message);
    }
}

async function deleteBook(id) {
    if (!confirm("Are you sure you want to delete this book?")) return;

    try {
        await api("/books/" + id, "DELETE");
        toast("Book deleted successfully");
        await loadBooks();
        await loadDashboard();
    } catch (e) {
        toast(e.message);
    }
}

// MEMBERS

function openMemberForm() {
    document.getElementById("memberForm").classList.remove("hidden");
}

function closeMemberForm() {
    document.getElementById("memberForm").classList.add("hidden");
}

async function saveMember() {
    const data = {
        name: document.getElementById("memberName").value.trim(),
        email: document.getElementById("memberEmail").value.trim(),
        phone: document.getElementById("memberPhone").value.trim()
    };

    if (Object.values(data).some(v => !v)) {
        return toast("Please fill all fields");
    }

    try {
        await api("/members", "POST", data);
        toast("Member added successfully");

        ["memberName", "memberEmail", "memberPhone"].forEach(id => {
            document.getElementById(id).value = "";
        });

        closeMemberForm();
        await loadMembers();
        await loadDashboard();
    } catch (e) {
        toast(e.message);
    }
}

async function loadMembers() {
    try {
        const members = await api("/members");

        document.getElementById("memberTable").innerHTML =
            members.map(m => `
                <tr>
                    <td>${m.id}</td>
                    <td>${escapeHTML(m.name)}</td>
                    <td>${escapeHTML(m.email)}</td>
                    <td>${escapeHTML(m.phone)}</td>
                    <td>
                        <button class="danger" onclick="deleteMember(${m.id})">Delete</button>
                    </td>
                </tr>
            `).join("") || emptyRow(5);
    } catch (e) {
        toast(e.message);
    }
}

async function deleteMember(id) {
    if (!confirm("Delete this member?")) return;

    try {
        await api("/members/" + id, "DELETE");
        toast("Member deleted successfully");
        await loadMembers();
        await loadDashboard();
    } catch (e) {
        toast(e.message);
    }
}

// ISSUE AND RETURN

async function loadIssuePage() {
    try {
        const [books, members, transactions] = await Promise.all([
            api("/books"),
            api("/members"),
            api("/transactions")
        ]);

        document.getElementById("issueBook").innerHTML =
            '<option value="">Select Available Book</option>' +
            books.filter(b => b.available).map(b =>
                `<option value="${b.id}">${escapeHTML(b.title)} - ${escapeHTML(b.author)}</option>`
            ).join("");

        document.getElementById("issueMember").innerHTML =
            '<option value="">Select Member</option>' +
            members.map(m =>
                `<option value="${m.id}">${escapeHTML(m.name)}</option>`
            ).join("");

        document.getElementById("transactionTable").innerHTML =
            transactions.map(t => `
                <tr>
                    <td>${t.id}</td>
                    <td>${escapeHTML(t.book_title)}</td>
                    <td>${escapeHTML(t.member_name)}</td>
                    <td>${escapeHTML(t.issue_date)}</td>
                    <td>${escapeHTML(t.return_date || "-")}</td>
                    <td>
                        ${t.status === "Issued"
                            ? '<span class="status issued">Issued</span>'
                            : '<span class="status available">Returned</span>'}
                    </td>
                    <td>
                        ${t.status === "Issued"
                            ? `<button class="primary" onclick="returnBook(${t.id})">Return</button>`
                            : "-"}
                    </td>
                </tr>
            `).join("") || emptyRow(7);

    } catch (e) {
        toast(e.message);
    }
}

async function issueBook() {
    const book_id = document.getElementById("issueBook").value;
    const member_id = document.getElementById("issueMember").value;

    if (!book_id || !member_id) {
        return toast("Select a book and member");
    }

    try {
        await api("/issue", "POST", {
            book_id: Number(book_id),
            member_id: Number(member_id)
        });

        toast("Book issued successfully");

        await loadIssuePage();
        await loadDashboard();
        await loadBooks();
    } catch (e) {
        toast(e.message);
    }
}

async function returnBook(id) {
    if (!confirm("Confirm book return?")) return;

    try {
        await api("/return/" + id, "PUT");
        toast("Book returned successfully");

        await loadIssuePage();
        await loadDashboard();
        await loadBooks();
    } catch (e) {
        toast(e.message);
    }
}

// INITIAL LOAD

document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});
