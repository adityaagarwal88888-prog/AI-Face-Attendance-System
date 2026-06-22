from flask import (
    Flask,
    render_template,
    session,
    redirect
)

from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp

from models.db import get_db_connection

app = Flask(__name__)

app.secret_key = "supersecretkey"


# REGISTER BLUEPRINTS

app.register_blueprint(auth_bp)

app.register_blueprint(student_bp)

app.register_blueprint(attendance_bp)


# HOME PAGE

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# DASHBOARD

@app.route("/dashboard/")
def dashboard():

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect(
            "/login"
        )

    teacher_id = session[
        "teacher_id"
    ]

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

    # TOTAL STUDENTS

    cursor.execute(
        """
        SELECT COUNT(*) AS total_students
        FROM students
        WHERE teacher_id=%s
        """,
        (teacher_id,)
    )

    total_students = cursor.fetchone()[
        "total_students"
    ]

    # TOTAL CLASSES

    cursor.execute(
        """
        SELECT COUNT(*) AS total_classes
        FROM classes
        """
    )

    total_classes = cursor.fetchone()[
        "total_classes"
    ]

    # TOTAL ATTENDANCE

    cursor.execute(
        """
        SELECT COUNT(*) AS total_attendance
        FROM attendance
        WHERE teacher_id=%s
        """,
        (teacher_id,)
    )

    total_attendance = cursor.fetchone()[
        "total_attendance"
    ]

    # TODAY ATTENDANCE

    cursor.execute(
        """
        SELECT COUNT(*) AS today_attendance
        FROM attendance
        WHERE date = CURDATE()
        AND teacher_id=%s
        """,
        (teacher_id,)
    )

    today_attendance = cursor.fetchone()[
        "today_attendance"
    ]

    # TOTAL ATTENDANCE DAYS

    cursor.execute(
        """
        SELECT COUNT(DISTINCT date) AS total_days
        FROM attendance
        WHERE teacher_id=%s
        """,
        (teacher_id,)
    )

    total_days_data = cursor.fetchone()

    total_days = total_days_data[
        "total_days"
    ]

    # OVERALL %

    overall_percentage = 0

    if total_students > 0 and total_days > 0:

        max_possible_attendance = (
            total_students *
            total_days
        )

        overall_percentage = round(
            (
                total_attendance /
                max_possible_attendance
            ) * 100,
            1
        )

    # TREND GRAPH

    cursor.execute(
        """
        SELECT
            DATE(date) AS attendance_date,
            COUNT(*) AS total
        FROM attendance
        WHERE teacher_id=%s
        GROUP BY attendance_date
        ORDER BY attendance_date ASC
        LIMIT 7
        """,
        (teacher_id,)
    )

    trend_data = cursor.fetchall()

    trend_labels = []

    trend_counts = []

    for row in trend_data:

        trend_labels.append(
            str(row["attendance_date"])
        )

        trend_counts.append(
            row["total"]
        )

    # TOP STUDENTS

    cursor.execute(
        """
        SELECT
            student_name,
            COUNT(*) AS total_present
        FROM attendance
        WHERE teacher_id=%s
        GROUP BY student_name
        ORDER BY total_present DESC
        LIMIT 5
        """,
        (teacher_id,)
    )

    top_students = cursor.fetchall()

    cursor.close()

    conn.close()

    return render_template(

        "dashboard.html",

        total_students=total_students,

        total_classes=total_classes,

        total_attendance=total_attendance,

        today_attendance=today_attendance,

        trend_labels=trend_labels,

        trend_counts=trend_counts,

        overall_percentage=overall_percentage,

        top_students=top_students
    )


# RUN APP

if __name__ == "__main__":

    app.run(debug=True)