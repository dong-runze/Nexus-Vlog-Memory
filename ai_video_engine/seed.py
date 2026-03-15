import os
import asyncio
from google.cloud import firestore

file_path = '.env'
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            if line.startswith('GOOGLE_APPLICATION_CREDENTIALS'):
                val = line.split('=')[1].strip().strip('"')
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = val
                break

# Initialize Firestore synchronously for the script
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
if project_id:
    db = firestore.AsyncClient(project=project_id)
else:
    db = firestore.AsyncClient()

DEFAULT_LANDMARKS = [
  {
    "id": '1',
    "name": 'Battlestar Galactica',
    "nameZh": '太空堡垒卡拉狄加',
    "category": 'landmark',
    "lat": 1.2550,
    "lng": 103.8218,
    "imageUrl": 'https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?w=800',
    "openingHours": 'Daily: 10:00 AM - 7:00 PM',
    "introduction": 'One of the tallest dueling roller coasters in the world, featuring Human and Cylon tracks in Sci-Fi City.',
    "introductionZh": '世界上最高的对决过山车之一，位于科幻城市区，分为人类和赛昂两条轨道，超级刺激！',
    "features": ['Roller Coaster', 'Thrill Ride', 'Sci-Fi City']
  },
  {
    "id": '2',
    "name": 'TRANSFORMERS The Ride',
    "nameZh": '变形金刚3D对决之终极战斗',
    "category": 'landmark',
    "lat": 1.2545,
    "lng": 103.8223,
    "imageUrl": 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=800',
    "openingHours": 'Daily: 10:00 AM - 7:00 PM',
    "introduction": 'An immersive 3D dark ride where you join the Autobots in the ultimate battle against the Decepticons.',
    "introductionZh": '沉浸式3D暗黑骑乘体验，加入汽车人与霸天虎展开终极对决！',
    "features": ['3D Ride', 'Dark Ride', 'Sci-Fi City']
  },
  {
    "id": '3',
    "name": 'Revenge of the Mummy',
    "nameZh": '木乃伊复仇记',
    "category": 'landmark',
    "lat": 1.2542,
    "lng": 103.8230,
    "imageUrl": 'https://images.unsplash.com/photo-1509248961187-54712a42e0f8?w=800',
    "openingHours": 'Daily: 10:00 AM - 7:00 PM',
    "introduction": 'A high-speed indoor roller coaster through ancient Egyptian tombs with special effects and sudden drops.',
    "introductionZh": '高速室内过山车，穿越古埃及墓穴，配合特效和突然坠落，惊险万分！',
    "features": ['Indoor Coaster', 'Special Effects', 'Ancient Egypt']
  },
  {
    "id": '4',
    "name": 'WaterWorld',
    "nameZh": '未来水世界',
    "category": 'school',
    "lat": 1.2555,
    "lng": 103.8237,
    "imageUrl": 'https://images.unsplash.com/photo-1504701954957-2010ec3bcec1?w=800',
    "openingHours": 'Showtimes: 12:30 PM, 2:00 PM, 5:30 PM',
    "introduction": 'A spectacular live stunt show featuring jet skis, explosions, and daring water stunts.',
    "introductionZh": '壮观的现场特技表演，包含水上摩托、爆炸和惊险的水上特技！',
    "features": ['Live Show', 'Stunts', 'The Lost World']
  },
  {
    "id": '5',
    "name": 'Jurassic Park Rapids Adventure',
    "nameZh": '侏罗纪公园河流探险',
    "category": 'landmark',
    "lat": 1.2558,
    "lng": 103.8230,
    "imageUrl": 'https://images.unsplash.com/photo-1606567595334-d39972c85dbe?w=800',
    "openingHours": 'Daily: 10:00 AM - 7:00 PM',
    "introduction": 'A thrilling river raft ride through the Jurassic era with animatronic dinosaurs and a steep plunge.',
    "introductionZh": '刺激的恐龙主题河流漂流，途经逼真的电动恐龙模型，最后从高处急速坠落！',
    "features": ['Water Ride', 'Dinosaurs', 'The Lost World']
  },
  {
    "id": '6',
    "name": 'Shrek 4-D Adventure',
    "nameZh": '怪物史瑞克4D影院',
    "category": 'school',
    "lat": 1.2548,
    "lng": 103.8248,
    "imageUrl": 'https://images.unsplash.com/photo-1596727147705-61a532a659bd?w=800',
    "openingHours": 'Daily: 10:00 AM - 7:00 PM',
    "introduction": 'A 4D adventure film experience in the magical kingdom of Far Far Away with Shrek and friends.',
    "introductionZh": '在遥远的童话王国体验4D冒险电影，和史瑞克一起踏上奇幻旅程！',
    "features": ['4D Theater', 'Family Friendly', 'Far Far Away']
  },
  {
    "id": '7',
    "name": "Mel's Drive-In",
    "nameZh": '梅尔斯经典快餐',
    "category": 'dining',
    "lat": 1.2538,
    "lng": 103.8242,
    "imageUrl": 'https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?w=800',
    "openingHours": 'Daily: 10:00 AM - 8:00 PM',
    "introduction": "A retro 1950s American diner serving classic burgers, fries, and milkshakes in the Hollywood zone.",
    "introductionZh": '复古50年代美式快餐厅，位于好莱坞区域，提供经典汉堡、薯条和奶昔。',
    "features": ['American Cuisine', 'Retro Diner', 'Hollywood Zone']
  },
  {
    "id": '8',
    "name": 'USS Globe Fountain',
    "nameZh": '环球影城标志性地球仪',
    "category": 'special',
    "lat": 1.2537,
    "lng": 103.8238,
    "imageUrl": 'https://images.unsplash.com/photo-1581351721010-8cf859cb14a4?w=800',
    "openingHours": 'Open during park hours',
    "introduction": 'The iconic rotating Universal globe at the park entrance - the ultimate USS photo spot!',
    "introductionZh": '环球影城入口处的标志性旋转地球仪——最经典的USS打卡拍照点！',
    "features": ['Photo Spot', 'Park Icon', 'Hollywood Zone']
  }
]

async def seed_database():
    try:
        col_ref = db.collection("landmarks")
        for landmark in DEFAULT_LANDMARKS:
            doc_id = landmark["id"]
            # Force add is_user_created: False for default set
            landmark["is_user_created"] = False
            landmark["room_code"] = "master" # Ensure backwards sandbox compat manually
            print(f"Seeding {landmark['name']}...")
            await col_ref.document(doc_id).set(landmark)
        
        print("Successfully seeded 8 landmarks into Firestore!")
    except Exception as e:
        print(f"An error occurred while seeding: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())
