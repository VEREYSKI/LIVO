"""Дополнительные фильмы каталога LIVO: (год, название, жанры)."""

_RAW = [
# 2000
(2000,"Crouching Tiger, Hidden Dragon","Боевик / Фэнтези"),(2000,"Almost Famous","Драма / Музыка"),(2000,"Traffic","Криминал / Драма"),
(2000,"Erin Brockovich","Драма"),(2000,"O Brother, Where Art Thou?","Комедия / Приключения"),(2000,"Final Destination","Ужасы / Триллер"),
(2000,"American Psycho","Триллер / Криминал"),(2000,"Billy Elliot","Драма / Музыка"),(2000,"Mission: Impossible 2","Боевик / Шпионский"),
(2000,"Chicken Run","Анимация / Комедия"),(2000,"Unbreakable","Триллер / Фантастика"),(2000,"Battle Royale","Триллер / Фантастика"),
# 2001
(2001,"Amélie","Романтика / Комедия"),(2001,"Donnie Darko","Фантастика / Триллер"),(2001,"Mulholland Drive","Триллер / Детектив"),
(2001,"Ocean’s Eleven","Криминал / Комедия"),(2001,"Monsters, Inc.","Анимация / Комедия"),(2001,"Moulin Rouge!","Мюзикл / Романтика"),
(2001,"The Others","Ужасы / Триллер"),(2001,"Training Day","Криминал / Триллер"),(2001,"Black Hawk Down","Военный / Боевик"),
(2001,"Legally Blonde","Комедия / Романтика"),(2001,"Ghost World","Драма / Комедия"),
# 2002
(2002,"Gangs of New York","Драма / Криминал"),(2002,"Minority Report","Фантастика / Триллер"),(2002,"City of God","Криминал / Драма"),
(2002,"Chicago","Мюзикл / Криминал"),(2002,"The Pianist","Драма / Военный"),(2002,"Signs","Фантастика / Триллер"),
(2002,"28 Days Later","Ужасы / Фантастика"),(2002,"Lilo & Stitch","Анимация / Семейный"),(2002,"Road to Perdition","Криминал / Драма"),
(2002,"Equilibrium","Фантастика / Боевик"),(2002,"Y Tu Mamá También","Драма / Романтика"),
# 2003
(2003,"Big Fish","Фэнтези / Драма"),(2003,"Oldboy","Триллер / Детектив"),(2003,"Mystic River","Драма / Криминал"),
(2003,"School of Rock","Комедия / Музыка"),(2003,"Love Actually","Романтика / Комедия"),(2003,"Bad Boys II","Боевик / Комедия"),
(2003,"Master and Commander: The Far Side of the World","Приключения / Военный"),(2003,"Elf","Комедия / Семейный"),
(2003,"Monster","Драма / Криминал"),(2003,"Memories of Murder","Криминал / Детектив"),(2003,"The Last Samurai","Боевик / Драма"),
# 2004
(2004,"Million Dollar Baby","Спорт / Драма"),(2004,"The Notebook","Романтика / Драма"),(2004,"Kill Bill: Vol. 2","Боевик / Криминал"),
(2004,"Shaun of the Dead","Комедия / Ужасы"),(2004,"Collateral","Криминал / Триллер"),(2004,"Hotel Rwanda","Драма / Военный"),
(2004,"Howl’s Moving Castle","Аниме / Фэнтези"),(2004,"The Aviator","Драма / Исторический"),(2004,"Sideways","Комедия / Драма"),
(2004,"I, Robot","Фантастика / Боевик"),(2004,"Downfall","Драма / Военный"),
# 2005
(2005,"Brokeback Mountain","Драма / Романтика"),(2005,"Charlie and the Chocolate Factory","Фэнтези / Семейный"),(2005,"Walk the Line","Музыка / Драма"),
(2005,"Munich","Триллер / Исторический"),(2005,"Mr. & Mrs. Smith","Боевик / Комедия"),(2005,"The 40-Year-Old Virgin","Комедия / Романтика"),
(2005,"War of the Worlds","Фантастика / Боевик"),(2005,"Crash","Драма / Криминал"),(2005,"Pride & Prejudice","Романтика / Драма"),
(2005,"Madagascar","Анимация / Комедия"),(2005,"Kingdom of Heaven","Исторический / Боевик"),
# 2006
(2006,"V for Vendetta","Фантастика / Боевик"),(2006,"Little Miss Sunshine","Комедия / Драма"),(2006,"The Devil Wears Prada","Комедия / Драма"),
(2006,"Children of Men","Фантастика / Триллер"),(2006,"Borat","Комедия"),(2006,"Happy Feet","Анимация / Музыка"),
(2006,"Apocalypto","Приключения / Боевик"),(2006,"Blood Diamond","Драма / Триллер"),(2006,"Letters from Iwo Jima","Военный / Драма"),
(2006,"The Queen","Драма / Исторический"),(2006,"The Host","Ужасы / Фантастика"),
# 2007
(2007,"Juno","Комедия / Драма"),(2007,"Superbad","Комедия"),(2007,"Into the Wild","Драма / Приключения"),
(2007,"Atonement","Драма / Романтика"),(2007,"The Bourne Ultimatum","Боевик / Шпионский"),(2007,"Hot Fuzz","Комедия / Боевик"),
(2007,"300","Боевик / Исторический"),(2007,"I Am Legend","Фантастика / Ужасы"),(2007,"Michael Clayton","Драма / Триллер"),
(2007,"The Simpsons Movie","Анимация / Комедия"),(2007,"Ratatouille: Remy’s Kitchen","Анимация / Семейный"),
# 2008
(2008,"The Curious Case of Benjamin Button","Драма / Фэнтези"),(2008,"Let the Right One In","Ужасы / Драма"),(2008,"In Bruges","Комедия / Криминал"),
(2008,"The Wrestler","Драма / Спорт"),(2008,"Tropic Thunder","Комедия / Боевик"),(2008,"Mamma Mia!","Мюзикл / Комедия"),
(2008,"Twilight","Фэнтези / Романтика"),(2008,"Cloverfield","Фантастика / Ужасы"),(2008,"Taken","Боевик / Триллер"),
(2008,"Ponyo","Аниме / Фэнтези"),(2008,"Vicky Cristina Barcelona","Романтика / Комедия"),
# 2009
(2009,"The Hurt Locker","Военный / Триллер"),(2009,"Zombieland","Комедия / Ужасы"),(2009,"(500) Days of Summer","Романтика / Комедия"),
(2009,"Star Trek","Фантастика / Приключения"),(2009,"Coraline","Анимация / Фэнтези"),(2009,"Fantastic Mr. Fox","Анимация / Комедия"),
(2009,"Up in the Air","Драма / Комедия"),(2009,"Paranormal Activity","Ужасы"),(2009,"Watchmen","Фантастика / Боевик"),
(2009,"Moon","Фантастика / Драма"),(2009,"The Princess and the Frog","Анимация / Мюзикл"),
# 2010
(2010,"True Grit","Вестерн / Драма"),(2010,"The King’s Speech","Драма / Исторический"),(2010,"The Fighter","Спорт / Драма"),
(2010,"Despicable Me","Анимация / Комедия"),(2010,"Kick-Ass","Боевик / Комедия"),(2010,"Scott Pilgrim vs. the World","Комедия / Фантастика"),
(2010,"Tangled","Анимация / Фэнтези"),(2010,"127 Hours","Драма / Приключения"),(2010,"The Town","Криминал / Драма"),
(2010,"The Expendables","Боевик"),(2010,"Winter’s Bone","Драма / Триллер"),
# 2011
(2011,"Midnight in Paris","Романтика / Фэнтези"),(2011,"Moneyball","Спорт / Драма"),(2011,"Hugo","Приключения / Семейный"),
(2011,"The Artist","Драма / Романтика"),(2011,"Tinker Tailor Soldier Spy","Шпионский / Триллер"),(2011,"Super 8","Фантастика / Приключения"),
(2011,"Crazy, Stupid, Love.","Комедия / Романтика"),(2011,"Mission: Impossible – Ghost Protocol","Боевик / Шпионский"),(2011,"Rango","Анимация / Вестерн"),
(2011,"The Girl with the Dragon Tattoo","Триллер / Детектив"),(2011,"Kung Fu Panda 2","Анимация / Комедия"),
# 2012
(2012,"Argo","Триллер / Драма"),(2012,"Looper","Фантастика / Боевик"),(2012,"Silver Linings Playbook","Романтика / Комедия"),
(2012,"Les Misérables","Мюзикл / Драма"),(2012,"Lincoln","Исторический / Драма"),(2012,"Moonrise Kingdom","Комедия / Романтика"),
(2012,"The Cabin in the Woods","Ужасы / Комедия"),(2012,"Ted","Комедия"),(2012,"Wreck-It Ralph","Анимация / Семейный"),
(2012,"Prometheus","Фантастика / Ужасы"),(2012,"21 Jump Street","Комедия / Боевик"),
# 2013
(2013,"12 Years a Slave","Драма / Исторический"),(2013,"Dallas Buyers Club","Драма"),(2013,"American Hustle","Криминал / Комедия"),
(2013,"Captain Phillips","Триллер / Драма"),(2013,"Rush","Спорт / Драма"),(2013,"Despicable Me 2","Анимация / Комедия"),
(2013,"The Conjuring","Ужасы"),(2013,"Iron Man 3","Боевик / Фантастика"),(2013,"The Hunger Games: Catching Fire","Фантастика / Приключения"),
(2013,"Inside Llewyn Davis","Драма / Музыка"),(2013,"The Great Beauty","Драма"),
# 2014
(2014,"Birdman","Драма / Комедия"),(2014,"Boyhood","Драма"),(2014,"The Imitation Game","Драма / Исторический"),
(2014,"Nightcrawler","Триллер / Криминал"),(2014,"Edge of Tomorrow","Фантастика / Боевик"),(2014,"Captain America: The Winter Soldier","Боевик / Фантастика"),
(2014,"How to Train Your Dragon 2","Анимация / Фэнтези"),(2014,"Big Hero 6","Анимация / Приключения"),(2014,"Fury","Военный / Драма"),
(2014,"The Theory of Everything","Драма / Романтика"),(2014,"X-Men: Days of Future Past","Боевик / Фантастика"),
# 2015
(2015,"Spotlight","Драма / Детектив"),(2015,"The Big Short","Драма / Комедия"),(2015,"Room","Драма / Триллер"),
(2015,"Ex Machina","Фантастика / Триллер"),(2015,"Creed","Спорт / Драма"),(2015,"Bridge of Spies","Шпионский / Драма"),
(2015,"Jurassic World","Фантастика / Приключения"),(2015,"Furious 7","Боевик / Гонки"),(2015,"The Hateful Eight","Вестерн / Криминал"),
(2015,"Kingsman: The Secret Service","Боевик / Шпионский"),(2015,"Brooklyn","Драма / Романтика"),
# 2016
(2016,"Manchester by the Sea","Драма"),(2016,"Hacksaw Ridge","Военный / Драма"),(2016,"Hell or High Water","Криминал / Драма"),
(2016,"Captain America: Civil War","Боевик / Фантастика"),(2016,"Rogue One: A Star Wars Story","Фантастика / Приключения"),(2016,"Finding Dory","Анимация / Семейный"),
(2016,"Fantastic Beasts and Where to Find Them","Фэнтези / Приключения"),(2016,"Your Name.","Аниме / Романтика"),(2016,"Train to Busan","Ужасы / Боевик"),
(2016,"10 Cloverfield Lane","Триллер / Фантастика"),(2016,"The Nice Guys","Комедия / Криминал"),
# 2017
(2017,"Three Billboards Outside Ebbing, Missouri","Драма / Криминал"),(2017,"Call Me by Your Name","Драма / Романтика"),(2017,"The Shape of Water","Фэнтези / Романтика"),
(2017,"Lady Bird","Драма / Комедия"),(2017,"Baby Driver","Криминал / Гонки"),(2017,"Logan","Боевик / Фантастика"),
(2017,"It","Ужасы"),(2017,"Star Wars: The Last Jedi","Фантастика / Приключения"),(2017,"The Greatest Showman","Мюзикл / Драма"),
(2017,"Jumanji: Welcome to the Jungle","Приключения / Комедия"),(2017,"Guardians of the Galaxy Vol. 2","Боевик / Фантастика"),
# 2018
(2018,"Roma","Драма"),(2018,"A Star Is Born","Музыка / Романтика"),(2018,"Green Book","Драма / Комедия"),
(2018,"BlacKkKlansman","Криминал / Драма"),(2018,"Mission: Impossible – Fallout","Боевик / Шпионский"),(2018,"Incredibles 2","Анимация / Семейный"),
(2018,"Searching","Триллер / Детектив"),(2018,"Annihilation","Фантастика / Триллер"),(2018,"Ready Player One","Фантастика / Приключения"),
(2018,"Venom","Боевик / Фантастика"),(2018,"Isle of Dogs","Анимация / Приключения"),
# 2019
(2019,"Once Upon a Time in Hollywood","Драма / Криминал"),(2019,"The Irishman","Криминал / Драма"),(2019,"Marriage Story","Драма"),
(2019,"Little Women","Драма / Романтика"),(2019,"Ford v Ferrari","Спорт / Гонки"),(2019,"Jojo Rabbit","Комедия / Военный"),
(2019,"Us","Ужасы / Триллер"),(2019,"Midsommar","Ужасы / Драма"),(2019,"Frozen II","Анимация / Мюзикл"),
(2019,"Rocketman","Музыка / Драма"),(2019,"Portrait of a Lady on Fire","Драма / Романтика"),
# 2020
(2020,"Nomadland","Драма"),(2020,"Onward","Анимация / Фэнтези"),(2020,"The Trial of the Chicago 7","Драма / Исторический"),
(2020,"Promising Young Woman","Триллер / Криминал"),(2020,"Mank","Драма / Исторический"),(2020,"Minari","Драма"),
(2020,"Bad Boys for Life","Боевик / Комедия"),(2020,"Wonder Woman 1984","Боевик / Фэнтези"),(2020,"Birds of Prey","Боевик / Криминал"),
(2020,"Sonic the Hedgehog","Приключения / Семейный"),(2020,"Over the Moon","Анимация / Мюзикл"),
# 2021
(2021,"The Power of the Dog","Вестерн / Драма"),(2021,"Nightmare Alley","Триллер / Криминал"),(2021,"West Side Story","Мюзикл / Романтика"),
(2021,"Shang-Chi and the Legend of the Ten Rings","Боевик / Фантастика"),(2021,"Free Guy","Комедия / Фантастика"),(2021,"A Quiet Place Part II","Ужасы / Фантастика"),
(2021,"Luca","Анимация / Семейный"),(2021,"CODA","Драма / Музыка"),(2021,"Belfast","Драма"),
(2021,"Don’t Look Up","Комедия / Фантастика"),(2021,"Raya and the Last Dragon","Анимация / Фэнтези"),
# 2022
(2022,"Nope","Ужасы / Фантастика"),(2022,"The Whale","Драма"),(2022,"Tár","Драма / Музыка"),
(2022,"Elvis","Музыка / Драма"),(2022,"Glass Onion: A Knives Out Mystery","Детектив / Комедия"),(2022,"Black Panther: Wakanda Forever","Боевик / Фантастика"),
(2022,"Puss in Boots: The Last Wish","Анимация / Приключения"),(2022,"Turning Red","Анимация / Комедия"),(2022,"RRR","Боевик / Исторический"),
(2022,"The Fabelmans","Драма"),(2022,"Bullet Train","Боевик / Комедия"),(2022,"The Menu","Ужасы / Комедия"),
# 2023
(2023,"Poor Things","Фантастика / Комедия"),(2023,"Killers of the Flower Moon","Криминал / Драма"),(2023,"Past Lives","Драма / Романтика"),
(2023,"Anatomy of a Fall","Драма / Детектив"),(2023,"The Zone of Interest","Драма / Военный"),(2023,"Mission: Impossible – Dead Reckoning Part One","Боевик / Шпионский"),
(2023,"The Super Mario Bros. Movie","Анимация / Семейный"),(2023,"Godzilla Minus One","Фантастика / Боевик"),(2023,"Wonka","Фэнтези / Мюзикл"),
(2023,"The Boy and the Heron","Аниме / Фэнтези"),(2023,"Talk to Me","Ужасы"),(2023,"Napoleon","Исторический / Драма"),
# 2024
(2024,"Anora","Драма / Комедия"),(2024,"The Brutalist","Драма"),(2024,"Challengers","Спорт / Романтика"),
(2024,"Civil War","Боевик / Триллер"),(2024,"A Complete Unknown","Музыка / Драма"),(2024,"Conclave","Триллер / Драма"),
(2024,"The Substance","Ужасы / Фантастика"),(2024,"Nosferatu","Ужасы / Фэнтези"),(2024,"Alien: Romulus","Ужасы / Фантастика"),
(2024,"Kung Fu Panda 4","Анимация / Комедия"),(2024,"Gladiator II","Боевик / Исторический"),(2024,"Moana 2","Анимация / Мюзикл"),
# 2025
(2025,"Mickey 17","Фантастика / Комедия"),(2025,"Captain America: Brave New World","Боевик / Фантастика"),(2025,"Mission: Impossible – The Final Reckoning","Боевик / Шпионский"),
(2025,"Jurassic World Rebirth","Фантастика / Приключения"),(2025,"Weapons","Ужасы / Триллер"),(2025,"Zootopia 2","Анимация / Комедия"),
(2025,"Wicked: For Good","Мюзикл / Фэнтези"),(2025,"Avatar: Fire and Ash","Фантастика / Приключения"),(2025,"One Battle After Another","Боевик / Драма"),
(2025,"Frankenstein","Ужасы / Фантастика"),(2025,"KPop Demon Hunters","Анимация / Музыка"),(2025,"28 Years Later","Ужасы / Фантастика"),
(2025,"Final Destination: Bloodlines","Ужасы"),(2025,"Black Bag","Шпионский / Триллер"),
]

MOVIES_EXTRA = [
    {"title": t, "genre": g, "year": y, "rating": "—"} for y, t, g in _RAW
]
