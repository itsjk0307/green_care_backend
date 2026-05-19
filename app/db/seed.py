from sqlalchemy import select

from app.models.golf_course import GolfCourse


async def seed_golf_courses(db):
    courses = [
        {
            "name": "Saltbay Golf Club",
            "name_ko": "솔트베이 골프클럽",
            "address": "Yongin, Gyeonggi-do",
            "address_ko": "경기도 용인시",
            "map_image_path": "saltbay_golf_club.jpg",
        },
        {
            "name": "Maysa Green Golf Club",
            "name_ko": "메이사그린 골프클럽",
            "address": "Seoul",
            "address_ko": "서울특별시",
            "map_image_path": None,
        },
        {
            "name": "Oak Valley Golf Club",
            "name_ko": "오크밸리 골프클럽",
            "address": "Wonju, Gangwon-do",
            "address_ko": "강원도 원주시",
            "map_image_path": None,
        },
        {
            "name": "Bear Creek Golf Club",
            "name_ko": "베어크리크 골프클럽",
            "address": "Pocheon, Gyeonggi-do",
            "address_ko": "경기도 포천시",
            "map_image_path": None,
        },
        {
            "name": "Nam Seoul Golf Club",
            "name_ko": "남서울 골프클럽",
            "address": "Yongin, Gyeonggi-do",
            "address_ko": "경기도 용인시",
            "map_image_path": None,
        },
    ]

    for data in courses:
        result = await db.execute(select(GolfCourse).where(GolfCourse.name == data["name"]))
        if not result.scalar_one_or_none():
            course = GolfCourse(**data)
            db.add(course)

    await db.commit()
    print("[OK] Golf courses seeded!")
