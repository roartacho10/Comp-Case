"""Fictitious names, combined at random. Common first and last names by country."""

FIRST_NAMES = {
    "Brasil": ["Ana", "Beatriz", "Bruno", "Camila", "Carlos", "Daniela", "Eduardo", "Fernanda", "Gabriel",
               "Gustavo", "Isabela", "João", "Juliana", "Larissa", "Lucas", "Marcelo", "Mariana", "Mateus",
               "Natália", "Paulo", "Pedro", "Rafael", "Renata", "Rodrigo", "Thiago", "Vanessa", "Vinícius",
               "Aline", "André", "Bianca", "Caio", "Carolina", "Diego", "Felipe", "Gabriela", "Helena", "Igor",
               "Jéssica", "Leonardo", "Letícia", "Luana", "Marina", "Otávio", "Patrícia", "Priscila", "Ricardo",
               "Sabrina", "Tatiana", "Victor"],
    "México": ["Alejandro", "Andrea", "Carlos", "Daniela", "Diego", "Fernanda", "Javier", "Jimena", "José",
               "Luis", "María", "Mariana", "Miguel", "Paola", "Ricardo", "Sofía", "Valeria", "Ximena"],
    "Colômbia": ["Andrés", "Camilo", "Carolina", "Catalina", "Daniel", "Felipe", "Juan", "Laura", "Lucía",
                 "Manuela", "Natalia", "Santiago", "Sebastián", "Valentina"],
    "Argentina": ["Agustín", "Camila", "Facundo", "Florencia", "Joaquín", "Julieta", "Lucas", "Martina",
                  "Matías", "Micaela", "Nicolás", "Sofía", "Tomás"],
    "Chile": ["Benjamín", "Catalina", "Constanza", "Cristóbal", "Francisca", "Ignacio", "Javiera",
              "Joaquín", "Matías", "Sebastián", "Trinidad", "Vicente"],
}

LAST_NAMES = {
    "Brasil": ["Almeida", "Alves", "Araújo", "Barbosa", "Cardoso", "Carvalho", "Costa", "Dias", "Ferreira",
               "Gomes", "Lima", "Martins", "Melo", "Moreira", "Oliveira", "Pereira", "Ribeiro", "Rocha",
               "Santos", "Silva", "Souza", "Teixeira", "Azevedo", "Batista", "Campos", "Correia", "Freitas",
               "Mendes", "Monteiro", "Nascimento", "Nunes", "Pinto", "Ramos", "Vieira"],
    "México": ["Castillo", "Cruz", "Flores", "García", "Gómez", "Hernández", "Jiménez", "López", "Martínez",
               "Morales", "Ortiz", "Pérez", "Ramírez", "Reyes", "Sánchez", "Torres"],
    "Colômbia": ["Cárdenas", "Castro", "Díaz", "Fernández", "Gutiérrez", "Herrera", "Moreno", "Muñoz",
                 "Ospina", "Restrepo", "Rojas", "Vargas"],
    "Argentina": ["Acosta", "Benítez", "Fernández", "González", "Medina", "Paz", "Romero", "Ruiz", "Sosa",
                  "Suárez", "Torres"],
    "Chile": ["Araya", "Contreras", "Espinoza", "Fuentes", "Muñoz", "Rojas", "Soto", "Silva", "Valenzuela",
              "Vergara"],
}


def random_name(rng, country: str) -> str:
    return f"{rng.choice(FIRST_NAMES[country])} {rng.choice(LAST_NAMES[country])}"


def unique_name(rng, country: str, taken: set[str]) -> str:
    """A name not used yet (falls back to a numbered variant if the combinations run out)."""
    for _ in range(200):
        name = random_name(rng, country)
        if name not in taken:
            taken.add(name)
            return name
    k = 2
    while f"{name} {k}" in taken:
        k += 1
    taken.add(f"{name} {k}")
    return f"{name} {k}"
