from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from models.db import get_db_connection

import random
import smtplib

from email.mime.text import MIMEText


auth_bp = Blueprint(
    "auth",
    __name__
)


# EMAIL CONFIG

EMAIL_ADDRESS = "YOUR_GMAIL@gmail.com"

EMAIL_PASSWORD = "YOUR_APP_PASSWORD"


# REGISTER

@auth_bp.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        password = request.form["password"]

        hashed_password = generate_password_hash(
            password
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        # CHECK EXISTING EMAIL

        cursor.execute(
            """
            SELECT *
            FROM teachers
            WHERE email=%s
            """,
            (email,)
        )

        existing = cursor.fetchone()

        if existing:

            cursor.close()
            conn.close()

            return "Email already exists"

        # INSERT USER

        query = """
        INSERT INTO teachers
        (
            name,
            email,
            password
        )
        VALUES(%s, %s, %s)
        """

        cursor.execute(
            query,
            (
                name,
                email,
                hashed_password
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(
            "/login?registered=1"
        )

    return render_template(
        "register.html"
    )


# LOGIN

@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT *
        FROM teachers
        WHERE email=%s
        """

        cursor.execute(
            query,
            (email,)
        )

        teacher = cursor.fetchone()

        cursor.close()
        conn.close()

        # CHECK USER

        if teacher:

            password_match = check_password_hash(
                teacher["password"],
                password
            )

            if password_match:

                session["teacher_id"] = teacher["id"]

                session["teacher_name"] = teacher["name"]

                return redirect(
                    "/dashboard/"
                )

        return render_template(
            "login.html",
            error="Invalid Credentials"
        )

    return render_template(
        "login.html"
    )


# FORGOT PASSWORD

@auth_bp.route(
    "/forgot_password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM teachers
            WHERE email=%s
            """,
            (email,)
        )

        teacher = cursor.fetchone()

        cursor.close()
        conn.close()

        # EMAIL NOT FOUND

        if not teacher:

            return render_template(
                "forgot_password.html",
                error="Email not found"
            )

        # GENERATE OTP

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        # STORE SESSION

        session["reset_email"] = email

        session["reset_otp"] = otp

        # SEND EMAIL

        try:

            msg = MIMEText(
                f"""
Your OTP for password reset is:

{otp}

AI Attendance System
                """
            )

            msg["Subject"] = (
                "Password Reset OTP"
            )

            msg["From"] = EMAIL_ADDRESS

            msg["To"] = email

            server = smtplib.SMTP(
                "smtp.gmail.com",
                587
            )

            server.starttls()

            server.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            server.send_message(msg)

            server.quit()

            return redirect(
                "/verify_otp"
            )

        except Exception as e:

            print(e)

            return "Failed to send email"

    return render_template(
        "forgot_password.html"
    )


# VERIFY OTP

@auth_bp.route(
    "/verify_otp",
    methods=["GET", "POST"]
)
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        # CHECK OTP

        if entered_otp == session.get(
            "reset_otp"
        ):

            return redirect(
                "/reset_password"
            )

        return render_template(
            "verify_otp.html",
            error="Invalid OTP"
        )

    return render_template(
        "verify_otp.html"
    )


# RESET PASSWORD

@auth_bp.route(
    "/reset_password",
    methods=["GET", "POST"]
)
def reset_password():

    if request.method == "POST":

        new_password = request.form[
            "password"
        ]

        hashed_password = generate_password_hash(
            new_password
        )

        email = session.get(
            "reset_email"
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE teachers
            SET password=%s
            WHERE email=%s
            """,
            (
                hashed_password,
                email
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        # CLEAR SESSION

        session.pop(
            "reset_email",
            None
        )

        session.pop(
            "reset_otp",
            None
        )

        return redirect(
            "/login?reset=1"
        )

    return render_template(
        "reset_password.html"
    )


# LOGOUT

@auth_bp.route("/logout")
def logout():

    session.clear()

    return redirect("/login")