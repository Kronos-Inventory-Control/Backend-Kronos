"""
Crea el único usuario SUPER_ADMIN de Kronos Inventory Control.

Este script se ejecuta desde la terminal local.
No existe un endpoint público para crear este usuario.

Uso:
    python -m scripts.create_super_admin
"""

from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.security import hash_password
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import SessionLocal
from app.models.direccion import Direccion
from app.models.rol import Rol
from app.models.usuario import Usuario


def solicitar_datos() -> dict:
    """Solicita los datos iniciales del SUPER_ADMIN."""

    print("\n=== CREACIÓN DEL SUPER_ADMIN ===\n")

    identificacion_txt = input("Identificación (solo números): ").strip()
    nombre = input("Nombres: ").strip()
    apellidos = input("Apellidos: ").strip()
    email = input("Correo electrónico: ").strip().lower()
    telefono = input("Teléfono: ").strip()

    print("\n--- Dirección (Enter para dejar 'No especificado') ---")
    barrio = input("Barrio: ").strip() or "No especificado"
    ciudad = input("Ciudad: ").strip() or "No especificado"
    localidad = input("Localidad: ").strip() or "No especificado"
    direccion_completa = input("Dirección completa: ").strip() or "No especificado"

    if not identificacion_txt.isdigit():
        raise ValueError("La identificación debe contener solo números.")

    if not nombre or not apellidos:
        raise ValueError("Los nombres y apellidos son obligatorios.")

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Debes ingresar un correo electrónico válido.")

    if len(email) > 45:
        raise ValueError("El correo no puede superar los 45 caracteres.")

    if not telefono:
        raise ValueError("El teléfono es obligatorio.")

    password = getpass("Crea una contraseña (mínimo 12 caracteres): ")
    confirmation = getpass("Confirma la contraseña: ")

    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")

    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")

    return {
        "identificacion": int(identificacion_txt),
        "nombre": nombre,
        "apellidos": apellidos,
        "email": email,
        "telefono": telefono,
        "barrio": barrio,
        "ciudad": ciudad,
        "localidad": localidad,
        "direccion_completa": direccion_completa,
        "password": password,
    }


def crear_super_admin() -> None:
    """Crea el SUPER_ADMIN si todavía no existe."""

    db = SessionLocal()

    try:
        # 1. Comprobar si ya existe un SUPER_ADMIN.
        existing_admin = db.scalar(
            select(Usuario).where(Usuario.rol_idRol == UserRole.SUPER_ADMIN)
        )

        if existing_admin:
            print(
                "\nNo se puede crear otro SUPER_ADMIN."
                "\nYa existe uno registrado en Kronos."
            )
            return

        # 2. Solicitar los datos.
        datos = solicitar_datos()

        # 3. Comprobar si el correo o la identificación ya están registrados.
        existing_email = db.scalar(
            select(Usuario).where(Usuario.correoElectronico == datos["email"])
        )

        if existing_email:
            raise ValueError("Ese correo electrónico ya está registrado.")

        existing_id = db.get(Usuario, datos["identificacion"])

        if existing_id:
            raise ValueError("Esa identificación ya está registrada.")

        # 4. Convertir la contraseña en un hash Argon2id.
        password_hash = hash_password(datos["password"])

        # 5. Asegurar que el rol SUPER_ADMIN exista en la tabla `roles`.
        if db.get(Rol, UserRole.SUPER_ADMIN.value) is None:
            db.add(Rol(idRol=UserRole.SUPER_ADMIN.value, nombreRol="SUPER_ADMIN"))
            db.flush()

        # 6. Crear la dirección (el usuario la requiere).
        direccion = Direccion(
            barrio=datos["barrio"],
            ciudad=datos["ciudad"],
            localidad=datos["localidad"],
            direccionCompleta=datos["direccion_completa"],
        )
        db.add(direccion)
        db.flush()

        # 7. Crear el usuario con el rol SUPER_ADMIN.
        super_admin = Usuario(
            identificacion=datos["identificacion"],
            nombre=datos["nombre"],
            apellidos=datos["apellidos"],
            correoElectronico=datos["email"],
            telefono=datos["telefono"],
            contrasena=password_hash,
            rol_idRol=UserRole.SUPER_ADMIN.value,
            direccion_idDireccion=direccion.idDireccion,
            activo=True,
        )

        # 8. Guardar en MySQL.
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        print("\nSUPER_ADMIN creado correctamente.")
        print(f"Identificación: {super_admin.identificacion}")
        print(f"Correo: {super_admin.correoElectronico}")
        print("La contraseña se almacenó mediante Argon2id.")

    except IntegrityError:
        db.rollback()
        print(
            "\nNo se pudo crear el SUPER_ADMIN."
            "\nLa base de datos rechazó el registro por una restricción "
            "de unicidad. Es posible que otro proceso haya creado "
            "el administrador o que el correo ya exista."
        )

    except (ValueError, SQLAlchemyError) as error:
        db.rollback()
        print(f"\nNo se pudo completar la operación: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    crear_super_admin()
