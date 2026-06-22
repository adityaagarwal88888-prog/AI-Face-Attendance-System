import face_recognition
import os

def encode_faces(image_folder):
    known_encodings = []
    known_names = []

    for filename in os.listdir(image_folder):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            path = os.path.join(image_folder, filename)

            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)

            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(filename.split(".")[0])

    return known_encodings, known_names


def recognize_faces(group_image_path, known_encodings, known_names):
    image = face_recognition.load_image_file(group_image_path)

    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    detected_students = []

    for face_encoding in face_encodings:
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        
        if len(face_distances) == 0:
            continue

        best_match_index = face_distances.argmin()

        if face_distances[best_match_index] < 0.5:
            name = known_names[best_match_index]
            detected_students.append(name)

    return detected_students