
from app.infrastructure.database.session import SessionLocal
from app.models.rol import Rol
from app.domain.enums.user_role import UserRole


def registrar_roles():

    db = SessionLocal()

    roles = [
        (UserRole.CLIENTE, "CLIENTE"),
        (UserRole.PROVEEDOR, "PROVEEDOR"),
        (UserRole.JEFE, "JEFE"),
        (UserRole.EMPLEADO, "EMPLEADO"),
        (UserRole.SUPER_ADMIN, "SUPER_ADMIN"),
    ]

    try:
        for id_rol, nombre in roles:

            rol_existente = db.get(Rol, id_rol.value)

            if rol_existente is None:

                nuevo_rol = Rol(
                    idRol=id_rol.value,
                    nombreRol=nombre
                )

                db.add(nuevo_rol)

        db.commit()

        print("Roles registrados correctamente.")

    except Exception as error:
        db.rollback()
        print(f"Error al registrar los roles: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    registrar_roles()
