from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    make_response,
    session
)

import os
import csv
import face_recognition

from models.db import get_db_connection
from config import UPLOAD_FOLDER

attendance_bp = Blueprint(
    "attendance",
    __name__
)


# MARK ATTENDANCE

@attendance_bp.route(
    "/mark_attendance",
    methods=["GET", "POST"]
)
def mark_attendance():

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

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

        class_id = request.form["class_id"]

        subject_name = request.form[
            "subject_name"
        ]

        attendance_date = request.form[
            "attendance_date"
        ]

        # GROUP IMAGES

        group_images = request.files.getlist(
            "group_images"
        )

        # FETCH TEACHER STUDENTS

        cursor.execute(
            """
            SELECT *
            FROM students
            WHERE class_id=%s
            AND teacher_id=%s
            ORDER BY roll_no ASC
            """,
            (
                class_id,
                teacher_id
            )
        )

        students = cursor.fetchall()

        # CHECK EXISTING ATTENDANCE

        cursor.execute(
            """
            SELECT *
            FROM attendance
            WHERE subject=%s
            AND date=%s
            AND teacher_id=%s
            LIMIT 1
            """,
            (
                subject_name,
                attendance_date,
                teacher_id
            )
        )

        existing_attendance = cursor.fetchone()

        if existing_attendance:

            cursor.close()
            conn.close()

            return render_template(
                "upload_attendance.html",
                classes=classes,
                subjects=subjects,
                error=f"Attendance already marked for {subject_name} on {attendance_date}"
            )

        all_students = students.copy()

        marked_students = []

        # VALID FORMATS

        valid_extensions = (
            ".jpg",
            ".jpeg",
            ".png"
        )

        print(
            "\n======================================="
        )

        print(
            "🚀 AI Attendance Processing Started"
        )

        print(
            f"📚 Subject: {subject_name}"
        )

        print(
            f"📅 Attendance Date: {attendance_date}"
        )

        print(
            f"👨‍🏫 Teacher ID: {teacher_id}"
        )

        print(
            f"👥 Total Students: {len(students)}"
        )

        print(
            "=======================================\n"
        )

        # PROCESS IMAGES

        for group_image in group_images:

            try:

                # EMPTY FILE

                if group_image.filename == "":
                    continue

                # INVALID FORMAT

                if not group_image.filename.lower().endswith(
                    valid_extensions
                ):

                    print(
                        f"❌ Invalid File: {group_image.filename}"
                    )

                    continue

                # SAVE GROUP IMAGE

                group_path = os.path.join(
                    UPLOAD_FOLDER,
                    "group",
                    group_image.filename
                )

                group_image.save(group_path)

                print(
                    f"\n📸 Processing Classroom Image: {group_image.filename}"
                )

                # LOAD IMAGE

                unknown_image = face_recognition.load_image_file(
                    group_path
                )

                # FACE ENCODINGS

                unknown_encodings = face_recognition.face_encodings(
                    unknown_image
                )

                # NO FACE

                if len(unknown_encodings) == 0:

                    print(
                        "❌ No Faces Detected In This Image"
                    )

                    continue

                print(
                    f"🧠 Faces Found: {len(unknown_encodings)}"
                )

                # LOOP STUDENTS

                for student in students:

                    try:

                        # PREVENT DUPLICATES

                        if student["name"] in marked_students:

                            continue

                        # STUDENT FOLDER

                        student_folder = os.path.join(
                            UPLOAD_FOLDER,
                            "students",
                            student["name"]
                        )

                        if not os.path.exists(
                            student_folder
                        ):

                            print(
                                f"⚠ Missing Folder: {student['name']}"
                            )

                            continue

                        student_images = os.listdir(
                            student_folder
                        )

                        all_known_encodings = []

                        # LOAD STUDENT IMAGES

                        for image_name in student_images:

                            try:

                                if not image_name.lower().endswith(
                                    valid_extensions
                                ):

                                    continue

                                image_path = os.path.join(
                                    student_folder,
                                    image_name
                                )

                                known_image = face_recognition.load_image_file(
                                    image_path
                                )

                                encodings = face_recognition.face_encodings(
                                    known_image
                                )

                                if len(encodings) > 0:

                                    all_known_encodings.append(
                                        encodings[0]
                                    )

                            except Exception as e:

                                print(
                                    f"⚠ Encoding Error For {student['name']}: {e}"
                                )

                                continue

                        # NO VALID ENCODINGS

                        if len(all_known_encodings) == 0:

                            print(
                                f"⚠ No Encodings Found For: {student['name']}"
                            )

                            continue

                        # MATCH FACES

                        for unknown_encoding in unknown_encodings:

                            result = face_recognition.compare_faces(
                                all_known_encodings,
                                unknown_encoding,
                                tolerance=0.5
                            )

                            # MATCH FOUND

                            if True in result:

                                marked_students.append(
                                    student["name"]
                                )

                                print(
                                    f"✅ Detected: {student['name']}"
                                )

                                # CHECK EXISTING

                                cursor.execute(
                                    """
                                    SELECT *
                                    FROM attendance
                                    WHERE student_name=%s
                                    AND subject=%s
                                    AND teacher_id=%s
                                    AND date=%s
                                    """,
                                    (
                                        student["name"],
                                        subject_name,
                                        teacher_id,
                                        attendance_date
                                    )
                                )

                                existing = cursor.fetchone()

                                # INSERT ATTENDANCE

                                if not existing:

                                    cursor.execute(
                                        """
                                        INSERT INTO attendance
                                        (
                                            student_name,
                                            subject,
                                            date,
                                            teacher_id
                                        )
                                        VALUES(%s, %s, %s, %s)
                                        """,
                                        (
                                            student["name"],
                                            subject_name,
                                            attendance_date,
                                            teacher_id
                                        )
                                    )

                                    conn.commit()

                                    print(
                                        f"📝 Attendance Marked: {student['name']}"
                                    )

                                else:

                                    print(
                                        f"⚠ Already Marked: {student['name']}"
                                    )

                                break

                    except Exception as e:

                        print(
                            f"⚠ Student Processing Error: {e}"
                        )

                        continue

            except Exception as e:

                print(
                    f"⚠ Group Image Error: {e}"
                )

                continue

        # ABSENT STUDENTS

        absent_students = []

        print(
            "\n========== ATTENDANCE REPORT =========="
        )

        print(
            f"✅ Total Detected: {len(marked_students)}"
        )

        print(
            f"❌ Total Absent: {len(all_students) - len(marked_students)}"
        )

        print(
            "\n------ ABSENT STUDENTS ------"
        )

        for student in all_students:

            if student["name"] not in marked_students:

                absent_students.append(
                    student
                )

                print(
                    f"❌ Not Detected: {student['name']}"
                )

        print(
            "\n=======================================\n"
        )

        cursor.close()
        conn.close()

        return render_template(
            "attendance_result.html",
            students=marked_students,
            absent_students=absent_students,
            subject_name=subject_name,
            attendance_date=attendance_date
        )

    cursor.close()
    conn.close()

    return render_template(
        "upload_attendance.html",
        classes=classes,
        subjects=subjects
    )


# FINALIZE ATTENDANCE

@attendance_bp.route(
    "/finalize_attendance",
    methods=["POST"]
)
def finalize_attendance():

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

    subject_name = request.form[
        "subject_name"
    ]

    attendance_date = request.form[
        "attendance_date"
    ]

    selected_students = request.form.getlist(
        "selected_students"
    )

    conn = get_db_connection()

    cursor = conn.cursor()

    for student_name in selected_students:

        cursor.execute(
            """
            SELECT *
            FROM attendance
            WHERE student_name=%s
            AND subject=%s
            AND teacher_id=%s
            AND date=%s
            """,
            (
                student_name,
                subject_name,
                teacher_id,
                attendance_date
            )
        )

        existing = cursor.fetchone()

        if not existing:

            cursor.execute(
                """
                INSERT INTO attendance
                (
                    student_name,
                    subject,
                    date,
                    teacher_id
                )
                VALUES(%s, %s, %s, %s)
                """,
                (
                    student_name,
                    subject_name,
                    attendance_date,
                    teacher_id
                )
            )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        "/attendance_history"
    )


# ATTENDANCE HISTORY

@attendance_bp.route(
    "/attendance_history"
)
def attendance_history():

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

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

    cursor.execute(
        """
        SELECT DISTINCT date
        FROM attendance
        WHERE teacher_id=%s
        ORDER BY date DESC
        """,
        (teacher_id,)
    )

    dates = cursor.fetchall()

    attendance_history = []

    for row in dates:

        attendance_date = row["date"]

        cursor.execute(
            """
            SELECT *
            FROM attendance
            WHERE date=%s
            AND teacher_id=%s
            ORDER BY student_name ASC
            """,
            (
                attendance_date,
                teacher_id
            )
        )

        students = cursor.fetchall()

        present_count = len(students)

        attendance_percentage = 0

        if total_students > 0:

            attendance_percentage = round(
                (
                    present_count /
                    total_students
                ) * 100,
                1
            )

        attendance_history.append({

            "date": attendance_date,

            "students": students,

            "present_count": present_count,

            "percentage": attendance_percentage
        })

    cursor.close()
    conn.close()

    return render_template(
        "attendance_history.html",
        attendance_history=attendance_history,
        total_students=total_students
    )


# EXPORT CSV

@attendance_bp.route(
    "/export_attendance"
)
def export_attendance():

    # LOGIN CHECK

    if "teacher_id" not in session:

        return redirect("/login")

    teacher_id = session["teacher_id"]

    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )

    # FETCH ATTENDANCE

    cursor.execute(
        """
        SELECT *
        FROM attendance
        WHERE teacher_id=%s
        ORDER BY date DESC
        """,
        (teacher_id,)
    )

    attendance = cursor.fetchall()

    cursor.close()
    conn.close()

    # CSV FILE PATH

    csv_path = os.path.join(
        UPLOAD_FOLDER,
        "attendance_export.csv"
    )

    # CREATE CSV

    with open(
        csv_path,
        mode="w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        # HEADER

        writer.writerow([
            "Student Name",
            "Subject",
            "Date"
        ])

        # DATA

        for row in attendance:

            writer.writerow([

                row["student_name"],

                row["subject"],

                row["date"]

            ])

    # DOWNLOAD FILE

    response = make_response(
        open(
            csv_path,
            "rb"
        ).read()
    )

    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=attendance.csv"

    response.headers[
        "Content-Type"
    ] = "text/csv"

    return response