def is_professor(user):
    return user.groups.filter(name='Professor').exists()

def is_coordenador(user):
    return user.groups.filter(name='Coordenador').exists()

def is_tecnico(user):
    return user.groups.filter(name='Tecnico').exists()

def is_admin(user):
    return user.groups.filter(name='Administrador').exists() or user.is_superuser
