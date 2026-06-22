from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session
)

import os
import shutil

from models.db import get_db_connection
from config import UPLOAD_FOLDER

student_bp = Blueprint(
    "student",
    __name__
)


# ADD STUDENT

@student_bp.route(
    "/add_student",
    methods=["GET", "POST"]
)
def add_student():

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect("/login")

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

    # FETCH CLASSES

    cursor.execute(
        "SELECT * FROM classes"
    )

    classes = cursor.fetchall()

    # FETCH SUBJECTS

    cursor.execute(
        "SELECT * FROM subjects"
    )

    subjects = cursor.fetchall()

    # FORM SUBMIT

    if request.method == "POST":

        name = request.form["name"]

        roll_no = request.form["roll_no"]

        class_id = request.form["class_id"]

        subject_id = request.form["subject_id"]

        teacher_id = session["teacher_id"]

        # MULTIPLE IMAGES

        images = request.files.getlist(
            "images"
        )

        # CREATE STUDENT FOLDER

        student_folder = os.path.join(
            UPLOAD_FOLDER,
            "students",
            name
        )

        os.makedirs(
            student_folder,
            exist_ok=True
        )

        # SAVE IMAGES

        first_image_path = ""

        for index, image in enumerate(images):

            if image.filename == "":
                continue

            image_path = os.path.join(
                student_folder,
                f"{index + 1}.jpg"
            )

            image.save(image_path)

            # STORE FIRST IMAGE

            if index == 0:

              first_image_path = f"/static/uploads/students/{name}/{index + 1}.jpg"

        # INSERT STUDENT

        query = """
        INSERT INTO students
        (
            name,
            roll_no,
            class_id,
            subject_id,
            image_path,
            teacher_id
        )
        VALUES(%s, %s, %s, %s, %s, %s)
        """

        values = (
            name,
            roll_no,
            class_id,
            subject_id,
            first_image_path,
            teacher_id
        )

        cursor.execute(
            query,
            values
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(
            "/students"
        )

    return render_template(
        "add_student.html",
        classes=classes,
        subjects=subjects
    )


# STUDENTS PAGE

@student_bp.route("/students")
def students():

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

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

    # FETCH STUDENTS

    query = """
    SELECT
        students.id,
        students.name,
        students.roll_no,
        students.image_path,
        classes.class_name,
        subjects.subject_name

    FROM students

    LEFT JOIN classes
    ON students.class_id = classes.id

    LEFT JOIN subjects
    ON students.subject_id = subjects.id

    WHERE students.teacher_id=%s

    ORDER BY students.roll_no ASC
    """

    cursor.execute(
        query,
        (teacher_id,)
    )

    student_data = cursor.fetchall()

    # ATTENDANCE %

    for student in student_data:

        cursor.execute(
            """
            SELECT COUNT(*) AS present_days
            FROM attendance
            WHERE student_name=%s
            AND teacher_id=%s
            """,
            (
                student["name"],
                teacher_id
            )
        )

        present_data = cursor.fetchone()

        present_days = present_data[
            "present_days"
        ]

        percentage = 0

        if total_days > 0:

            percentage = round(
                (
                    present_days /
                    total_days
                ) * 100,
                1
            )

        # SAVE %

        student[
            "attendance_percentage"
        ] = percentage

        # STATUS

        if percentage >= 75:

            student[
                "attendance_status"
            ] = "Excellent"

            student[
                "attendance_color"
            ] = "green"

        elif percentage >= 50:

            student[
                "attendance_status"
            ] = "Average"

            student[
                "attendance_color"
            ] = "yellow"

        else:

            student[
                "attendance_status"
            ] = "Low"

            student[
                "attendance_color"
            ] = "red"

    cursor.close()
    conn.close()

    return render_template(
        "students.html",
        students=student_data
    )


# DELETE STUDENT

@student_bp.route(
    "/delete_student/<int:id>"
)
def delete_student(id):

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

    # FETCH STUDENT

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE id=%s
        AND teacher_id=%s
        """,
        (
            id,
            teacher_id
        )
    )

    student = cursor.fetchone()

    # DELETE FOLDER

    if student:

        student_folder = os.path.join(
            UPLOAD_FOLDER,
            "students",
            student["name"]
        )

        if os.path.exists(
            student_folder
        ):

            shutil.rmtree(
                student_folder
            )

    # DELETE RECORD

    cursor.execute(
        """
        DELETE FROM students
        WHERE id=%s
        AND teacher_id=%s
        """,
        (
            id,
            teacher_id
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        "/students"
    )