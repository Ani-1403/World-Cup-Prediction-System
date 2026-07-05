# Official 2026 FIFA World Cup squad lists for all Round of 16 teams
# still active (Canada and Paraguay excluded - eliminated in RO16).
# Source: Wikipedia / FIFA official squad lists, confirmed June 2026.
# Players listed as: "First Last" (position tag omitted for clean dropdowns).

SQUADS = {
    "Morocco": [
        # GK
        "Yassine Bounou", "Munir Mohamedi", "Ahmed Reda Tagnaouti",
        # DF
        "Achraf Hakimi", "Nayef Aguerd", "Noussair Mazraoui",
        "Youssef Belammari", "Anass Salah-Eddine", "Chadi Riad",
        "Issa Diop", "Zakaria El Ouahdi", "Redouane Halhal",
        # MF
        "Sofyan Amrabat", "Azzedine Ounahi", "Bilal El Khannouss",
        "Ismael Saibari", "Neil El Aynaoui", "Samir El Mourabet",
        "Ayyoub Bouaddi",
        # FW
        "Ayoub El Kaabi", "Soufiane Rahimi", "Abde Ezzalzouli",
        "Brahim Díaz", "Chemsdine Talbi", "Gessime Yassine",
        "Ayoube Amaimouni",
    ],

    "France": [
        # GK
        "Brice Samba", "Mike Maignan", "Robin Risser",
        # DF
        "Malo Gusto", "Lucas Digne", "Dayot Upamecano", "Jules Koundé",
        "Ibrahima Konaté", "William Saliba", "Théo Hernandez",
        "Lucas Hernandez", "Maxence Lacroix",
        # MF
        "Manu Koné", "Aurélien Tchouaméni", "N'Golo Kanté",
        "Adrien Rabiot", "Warren Zaïre-Emery",
        # FW
        "Kylian Mbappé", "Ousmane Dembélé", "Marcus Thuram",
        "Michael Olise", "Bradley Barcola", "Désiré Doué",
        "Jean-Philippe Mateta", "Rayan Cherki", "Maghnes Akliouche",
    ],

    "Brazil": [
        # GK
        "Alisson", "Weverton", "Ederson",
        # DF
        "Wesley", "Gabriel Magalhães", "Marquinhos", "Alex Sandro",
        "Danilo Luiz", "Bremer", "Léo Pereira", "Douglas Santos",
        "Roger Ibañez",
        # MF
        "Casemiro", "Bruno Guimarães", "Fabinho",
        "Danilo Santos", "Lucas Paquetá",
        # FW
        "Vinícius Júnior", "Matheus Cunha", "Neymar", "Raphinha",
        "Endrick", "Luiz Henrique", "Gabriel Martinelli",
        "Igor Thiago", "Rayan",
    ],

    "Norway": [
        # GK
        "Ørjan Nyland", "Sander Tangvik", "Egil Selvik",
        # DF
        "Kristoffer Ajer", "Leo Østigård", "David Møller Wolfe",
        "Fredrik André Bjørkan", "Marcus Holmgren Pedersen",
        "Torbjørn Heggem", "Sondre Langås", "Henrik Falchener",
        "Julian Ryerson",
        # MF
        "Morten Thorsby", "Patrick Berg", "Sander Berge",
        "Fredrik Aursnes", "Kristian Thorstvedt", "Thelo Aasgaard",
        "Antonio Nusa", "Andreas Schjelderup", "Oscar Bobb",
        "Jens Petter Hauge", "Martin Ødegaard",
        # FW
        "Alexander Sørloth", "Erling Haaland", "Jørgen Strand Larsen",
    ],

    "Mexico": [
        # GK
        "Guillermo Ochoa", "Raúl Rangel", "Carlos Acevedo",
        # DF
        "Jesús Gallardo", "César Montes", "Jorge Sánchez",
        "Johan Vásquez", "Israel Reyes", "Mateo Chávez",
        # MF
        "Edson Álvarez", "Orbelín Pineda", "Roberto Alvarado",
        "Luis Romo", "Luis Chávez", "Érik Lira", "Gilberto Mora",
        "Brian Gutiérrez", "Obed Vargas", "Álvaro Fidalgo",
        # FW
        "Raúl Jiménez", "Alexis Vega", "Santiago Giménez",
        "César Huerta", "Julián Quiñones", "Guillermo Martínez",
        "Armando González",
    ],

    "England": [
        # GK
        "Jordan Pickford", "Dean Henderson", "James Trafford",
        # DF
        "John Stones", "Marc Guéhi", "Reece James", "Ezri Konsa",
        "Dan Burn", "Tino Livramento", "Djed Spence",
        "Nico O'Reilly", "Jarell Quansah",
        # MF
        "Jordan Henderson", "Declan Rice", "Jude Bellingham",
        "Morgan Rogers", "Kobbie Mainoo", "Elliot Anderson",
        # FW
        "Harry Kane", "Marcus Rashford", "Bukayo Saka",
        "Ollie Watkins", "Anthony Gordon", "Eberechi Eze",
        "Noni Madueke", "Ivan Toney",
    ],

    "Portugal": [
        # GK
        "Diogo Costa", "José Sá", "Rui Silva",
        # DF
        "Rúben Dias", "João Cancelo", "Nélson Semedo",
        "Nuno Mendes", "Diogo Dalot", "Gonçalo Inácio",
        "Matheus Nunes", "Renato Veiga", "Tomás Araújo",
        # MF
        "Bernardo Silva", "Bruno Fernandes", "Rúben Neves",
        "Vitinha", "João Neves", "Samú Costa",
        # FW
        "Cristiano Ronaldo", "João Félix", "Rafael Leão",
        "Gonçalo Guedes", "Gonçalo Ramos", "Pedro Neto",
        "Francisco Trincão", "Francisco Conceição",
    ],

    "Spain": [
        # GK
        "David Raya", "Joan Garcia", "Unai Simón",
        # DF
        "Marc Pubill", "Álex Grimaldo", "Eric García",
        "Marcos Llorente", "Pedro Porro", "Aymeric Laporte",
        "Pau Cubarsí", "Marc Cucurella",
        # MF
        "Rodri", "Mikel Merino", "Fabián Ruiz", "Gavi",
        "Álex Baena", "Martín Zubimendi", "Pedri",
        # FW
        "Ferran Torres", "Dani Olmo", "Yéremy Pino",
        "Nico Williams", "Lamine Yamal", "Mikel Oyarzabal",
        "Víctor Muñoz", "Borja Iglesias",
    ],

    "USA": [
        # GK
        "Matt Turner", "Matt Freese", "Chris Brady",
        # DF
        "Sergiño Dest", "Chris Richards", "Antonee Robinson",
        "Auston Trusty", "Miles Robinson", "Alex Freeman",
        "Maximilian Arfsten", "Mark McKenzie", "Joe Scally",
        "Tim Ream",
        # MF
        "Tyler Adams", "Giovanni Reyna", "Weston McKennie",
        "Sebastian Berhalter", "Cristian Roldan", "Malik Tillman",
        # FW
        "Christian Pulisic", "Ricardo Pepi", "Brenden Aaronson",
        "Haji Wright", "Folarin Balogun", "Timothy Weah",
        "Alejandro Zendejas",
    ],

    "Belgium": [
        # GK
        "Thibaut Courtois", "Senne Lammens", "Mike Penders",
        # DF
        "Thomas Meunier", "Timothy Castagne", "Arthur Theate",
        "Zeno Debast", "Maxim De Cuyper", "Brandon Mechele",
        "Koni De Winter", "Joaquin Seys", "Nathan Ngoy",
        # MF
        "Axel Witsel", "Kevin De Bruyne", "Youri Tielemans",
        "Hans Vanaken", "Amadou Onana", "Nicolas Raskin",
        # FW
        "Romelu Lukaku", "Leandro Trossard", "Jérémy Doku",
        "Dodi Lukébakio", "Charles De Ketelaere",
        "Alexis Saelemaekers", "Diego Moreira",
        "Matias Fernandez-Pardo",
    ],

    "Argentina": [
        # GK
        "Juan Musso", "Gerónimo Rulli", "Emiliano Martínez",
        # DF
        "Leonardo Balerdi", "Nicolás Tagliafico", "Gonzalo Montiel",
        "Lisandro Martínez", "Cristian Romero", "Nicolás Otamendi",
        "Facundo Medina", "Nahuel Molina",
        # MF
        "Leandro Paredes", "Rodrigo De Paul", "Valentín Barco",
        "Giovani Lo Celso", "Exequiel Palacios", "Alexis Mac Allister",
        "Enzo Fernández",
        # FW
        "Lionel Messi", "Julián Alvarez", "Nicolás González",
        "Thiago Almada", "Giuliano Simeone", "Nico Paz",
        "José Manuel López", "Lautaro Martínez",
    ],

    "Egypt": [
        # GK
        "Mohamed El Shenawy", "Mostafa Shobeir", "Mohamed Alaa",
        "El Mahdy Soliman",
        # DF
        "Hamdy Fathy", "Ramy Rabia", "Mohamed Hany", "Ahmed Fatouh",
        "Mohamed Abdelmonem", "Yasser Ibrahim", "Hossam Abdelmaguid",
        "Karim Hafez", "Tarek Alaa",
        # MF
        "Marwan Attia", "Emam Ashour", "Mohanad Lasheen",
        "Mahmoud Saber", "Nabil Emad", "Mostafa Ziko",
        # FW
        "Mohamed Salah", "Trézéguet", "Zizo", "Omar Marmoush",
        "Ibrahim Adel", "Haissem Hassan", "Hamza Abdelkarim",
    ],

    "Switzerland": [
        # GK
        "Gregor Kobel", "Yvon Mvogo", "Marvin Keller",
        # DF
        "Miro Muheim", "Silvan Widmer", "Nico Elvedi",
        "Manuel Akanji", "Ricardo Rodriguez", "Eray Cömert",
        "Aurèle Amenda", "Luca Jaquez",
        # MF
        "Granit Xhaka", "Denis Zakaria", "Remo Freuler",
        "Johan Manzambi", "Ardon Jashari", "Djibril Sow",
        "Christian Fassnacht", "Michel Aebischer", "Fabian Rieder",
        # FW
        "Breel Embolo", "Dan Ndoye", "Rubén Vargas",
        "Noah Okafor", "Zeki Amdouni", "Cedric Itten",
    ],

    "Colombia": [
        # GK
        "David Ospina", "Camilo Vargas", "Álvaro Montero",
        # DF
        "Davinson Sánchez", "Santiago Arias", "Yerry Mina",
        "Daniel Muñoz", "Johan Mojica", "Jhon Lucumí",
        "Deiver Machado", "Willer Ditta",
        # MF
        "James Rodríguez", "Jefferson Lerma", "Juan Fernando Quintero",
        "Jhon Arias", "Richard Ríos", "Kevin Castaño",
        "Jorge Carrascal", "Jaminton Campaz", "Juan Portilla",
        "Gustavo Puerta",
        # FW
        "Luis Díaz", "Jhon Córdoba", "Luis Suárez",
        "Cucho Hernández", "Andrés Gómez",
    ],
}


def get_squad(team_name: str) -> list[str]:
    """
    Returns the sorted squad list for a team, or an empty list if the
    team is not found (e.g. a QF/SF team whose RO16 opponent's squad
    isn't tracked here yet).
    """
    return sorted(SQUADS.get(team_name, []))


def get_combined_squad(team1: str, team2: str) -> tuple[list[str], list[str]]:
    """Returns (squad1, squad2) both sorted alphabetically."""
    return get_squad(team1), get_squad(team2)
