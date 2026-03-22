#!/usr/bin/env python3
"""Build preset compatibility graph keyed by preset id using taxonomy-first rules.

Design:
- Default deny (no compatibility edge).
- Explicit allow via semantic family compatibility.
- Hard blocks for known non-place/structural classes.
- Self edge always included.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Structural/non-place presets: never broadly merge.
BLOCK_KEYS = {
    "emergency",
    "barrier",
    "traffic_calming",
    "traffic_sign",
    "crossing",
    "man_made",
}

TRANSIT_KEYS = {"railway", "public_transport", "aerialway", "aeroway"}

# Explicit pairwise exceptions approved from real-world audits.
# Keep this small and intentional.
FORCED_ALLOW_PAIRS: Set[Tuple[int, int]] = {
    (72, 36),     # Cafe <-> Community Center
    (189, 970),   # Embassy <-> Embassy Others
    (416, 659),   # Sports Club <-> Bowling Alley
    (503, 603),   # Driving Range <-> Golf Course
    (731, 1201),  # Yoga Studio <-> Sporting Goods Store
    (1174, 1449), # Electronics Store <-> Event Photography
    (1144, 1461), # Cannabis Shop <-> Cannabis Clinic
    (62, 583),    # Bar <-> Dance Hall
    (969, 189),   # Consulate <-> Embassy
    (971, 189),   # Liaison Office <-> Embassy
    (1157, 72),   # Coffee Store <-> Cafe
    (1155, 1504), # Chocolate Store <-> Desserts
    (155, 1155),  # Restaurant <-> Chocolate Store
    (1235, 1504), # Pastry Shop <-> Desserts
    (107, 928),   # Hospital Grounds <-> Nonprofit Office
    (2653, 242),  # Entrance <-> Italian Restaurant
    (98, 1268),   # Fast Food <-> Video Game Store
    (290, 62),    # Transit Ticket Vending Machine <-> Bar
    (72, 1736),   # Cafe <-> Cupcake Shop
    (498, 1432),  # Main Entrance <-> Real Estate Agent
    (1161, 1540), # Fabric Store <-> Furniture Assembly
    (498, 1563),  # Main Entrance <-> Jewelry and Watches Manufacturer
    (1090, 926),  # Copy Store <-> Advertising Agency
    (2653, 1208), # Entrance <-> Jewelry Store
    (1219, 958),  # Medical Supply Store <-> Research Office
    (432, 1164),  # Dressmaker <-> Arts & Crafts Store
    (1208, 1563), # Jewelry Store <-> Jewelry and Watches Manufacturer
    (2653, 1241), # Entrance <-> Photography Store
    (1131, 1504), # Beauty Shop <-> Desserts
    (1276, 1525), # Wine Shop <-> Wine Bar
    (2647, 1156), # Soccer <-> Clothing Store
    (2653, 502),  # Entrance <-> Optometrist
    (134, 988),   # Parking Lot <-> Square
    (967, 1262),  # Travel Agent <-> Travel Agency
    (2246, 1411), # Religious Destination <-> Landmark and Historical Building
    (1226, 59),   # Music Store <-> Arts Center
    (94, 1411),   # Drinking Water <-> Landmark and Historical Building
    (2653, 1484), # Entrance <-> Flowers and Gifts Shop
    (101, 1411),  # Fountain <-> Landmark and Historical Building
    (432, 1156),  # Dressmaker <-> Clothing Store
    (458, 1234),  # Shoemaker <-> Shoe Repair Shop
    (592, 1411),  # Monument <-> Landmark and Historical Building
    (1268, 1454), # Video Game Store <-> Software Development
    (1504, 1736), # Desserts <-> Cupcake Shop
    (933, 145),   # Educational Institution <-> Test Prep / Tutoring School
    (1028, 1463), # Subway Entrance <-> Transportation
    (221, 134),   # Underground Parking <-> Parking Lot
    (124, 1255),  # Marketplace <-> Supermarket
    (135, 134),   # Parking Garage Entrance / Exit <-> Parking Lot
    (1306, 1411), # Hotel <-> Landmark and Historical Building
    (933, 1132),  # Educational Institution <-> Elementary School
    (81, 517),    # Clinic <-> Counselling Center
    (1226, 131),  # Music Store <-> Music School
    (81, 1446),   # Clinic <-> Medical Service Organizations
    (2651, 722),  # Gymnastics <-> Sports Center / Complex
    (155, 1736),  # Restaurant <-> Cupcake Shop
    (1157, 196),  # Coffee Store <-> Coffeehouse
    (1401, 1118), # Building <-> Event Planning
    (1221, 962),  # Mobile Phone Store <-> Telecom Office
    (703, 1411),  # Garden <-> Landmark and Historical Building
    (81, 1477),   # Clinic <-> Physical Therapy
    (62, 1575),   # Bar <-> Jazz and Blues
    (712, 1298),  # Park <-> Tourist Attraction
    (712, 988),   # Park <-> Square
    (132, 583),   # Nightclub <-> Dance Hall
    (158, 933),   # School Grounds <-> Educational Institution
    (1154, 76),   # Drugstore <-> Pharmacy Counter
    (1230, 502),  # Optician <-> Optometrist
    (36, 170),    # Community Center <-> Theater
    (36, 59),     # Community Center <-> Arts Center
    (1067, 1463), # Tram & Bus Stop <-> Transportation
    (1061, 1463), # Tram Stopping Location <-> Transportation
    (1064, 1463), # Bus Platform <-> Transportation
    (928, 170),   # Nonprofit Office <-> Theater
    (115, 1132),  # Language School <-> Elementary School
    (1008, 1463), # Bus Stopping Location <-> Transportation
    (704, 1118),  # Hackerspace <-> Event Planning
    (1174, 2385), # Electronics Store <-> Domestic Business and Trade Organizations
    (1194, 1406), # Gift Shop <-> Professional Services
    (1276, 155),  # Wine Shop <-> Restaurant
    (1401, 592),  # Building <-> Monument
    (1401, 140),  # Building <-> Police
    (498, 1309),  # Main Entrance <-> Museum
    (1131, 91),   # Beauty Shop <-> Doctor
    (1044, 1463), # Light Rail Station <-> Transportation
    (1298, 1421), # Tourist Attraction <-> Cathedral
    (426, 1255),  # Caterer <-> Supermarket
    (448, 926),   # Photographic Laboratory <-> Advertising Agency
    (448, 1719),  # Photographic Laboratory <-> Business Management Services
    (931, 1766),  # Consultancy Office <-> Occupational Safety
    (1401, 1484), # Building <-> Flowers and Gifts Shop
    (1327, 943),  # Visitor Center <-> Government Office
    (645, 943),   # Cemetery <-> Government Office
    (513, 1280),  # Alternative Medicine <-> Shop
    (933, 2033),  # Educational Institution <-> Adult Education
    (956, 87),    # Quasi-NGO Office <-> Courthouse
    (2549, 1230), # Retina Specialist <-> Optician
    (155, 431),   # Restaurant <-> Distillery
    (1159, 1570), # Computer Store <-> Computer Hardware Company
    (2446, 519),  # Diagnostic Imaging <-> Medical Laboratory
    (147, 423),   # Pub <-> Brewery
    (626, 592),   # Memorial <-> Monument
    (2035, 517),  # Volunteer Association <-> Counselling Center
    (928, 416),   # Nonprofit Office <-> Sports Club
    (1947, 517),  # Psychiatrist <-> Counselling Center
    (416, 1437),  # Sports Club <-> Martial Arts Club
    (264, 1306),  # Nursing Facility <-> Hotel
    (714, 1522),  # Sport Pitch <-> Rock Climbing Spot
    (928, 1180),  # Nonprofit Office <-> Artwork
    (132, 170),   # Nightclub <-> Theater
    (930, 1174),  # Corporate Office <-> Electronics Store
    (158, 131),   # School Grounds <-> Music School
    (915, 163),   # Charity Office <-> Social Facility
    (522, 1477),  # Physiotherapist <-> Physical Therapy
    (190, 1492),  # Nursing Home <-> Retirement Home
    (147, 1637),  # Pub <-> Pool Billiards
    (1133, 1674), # Bedding/Mattress Store <-> Business To Business Services
    (935, 2412),  # Energy Supplier Office <-> Electrical Wholesaler
    (2446, 1828), # Diagnostic Imaging <-> Radiologist
    (780, 1522),  # Climbing Gym <-> Rock Climbing Spot
    (59, 1604),   # Arts Center <-> Masonry Concrete
    (36, 2668),   # Community Center <-> Religious Organization
    (76, 1219),   # Pharmacy Counter <-> Medical Supply Store
    (1066, 1180), # Art Store <-> Artwork
    (434, 1756),  # Electrician <-> Energy Equipment and Solution
    (76, 2581),   # Pharmacy Counter <-> Pharmaceutical Products Wholesaler
    (1401, 62),   # Building <-> Bar
    (1, 793),  # auto sem>=0.95 Bridge <-> Bridge Area
    (65, 175),  # auto sem>=0.95 Bicycle Parking <-> Bicycle Parking Garage
    (82, 178),  # auto sem>=0.95 Bread Vending Machine <-> Vending Machine
    (82, 277),  # auto sem>=0.95 Bread Vending Machine <-> Drink Vending Machine
    (82, 278),  # auto sem>=0.95 Bread Vending Machine <-> Egg Vending Machine
    (82, 284),  # auto sem>=0.95 Bread Vending Machine <-> Food Vending Machine
    (82, 286),  # auto sem>=0.95 Bread Vending Machine <-> Ice Cream Vending Machine
    (82, 287),  # auto sem>=0.95 Bread Vending Machine <-> Ice Vending Machine
    (82, 289),  # auto sem>=0.95 Bread Vending Machine <-> Pizza Vending Machine
    (82, 292),  # auto sem>=0.95 Bread Vending Machine <-> Snack Vending Machine
    (88, 2071),  # auto sem>=0.95 Crematorium <-> Pet Cemetery and Crematorium Services
    (91, 2328),  # auto sem>=0.95 Doctor <-> Emergency Medicine
    (92, 1437),  # auto sem>=0.95 Dojo / Martial Arts Academy <-> Martial Arts Club
    (92, 2545),  # auto sem>=0.95 Dojo / Martial Arts Academy <-> Karate Club
    (102, 1858),  # auto sem>=0.95 Gas Station <-> Oil Change Station
    (102, 2543),  # auto sem>=0.95 Gas Station <-> Truck Gas Station
    (132, 216),  # auto sem>=0.95 Nightclub <-> LGBTQ+ Nightclub
    (132, 1575),  # auto sem>=0.95 Nightclub <-> Jazz and Blues
    (132, 1853),  # auto sem>=0.95 Nightclub <-> Salsa Club
    (132, 2580),  # auto sem>=0.95 Nightclub <-> Club Crawl
    (151, 152),  # auto sem>=0.95 Recycling Center <-> Recycling Container
    (178, 275),  # auto sem>=0.95 Vending Machine <-> Coffee Vending Machine
    (178, 276),  # auto sem>=0.95 Vending Machine <-> Condom Vending Machine
    (178, 277),  # auto sem>=0.95 Vending Machine <-> Drink Vending Machine
    (178, 278),  # auto sem>=0.95 Vending Machine <-> Egg Vending Machine
    (178, 284),  # auto sem>=0.95 Vending Machine <-> Food Vending Machine
    (178, 287),  # auto sem>=0.95 Vending Machine <-> Ice Vending Machine
    (178, 289),  # auto sem>=0.95 Vending Machine <-> Pizza Vending Machine
    (178, 292),  # auto sem>=0.95 Vending Machine <-> Snack Vending Machine
    (179, 2378),  # auto sem>=0.95 Veterinary <-> Emergency Pet Hospital
    (187, 1495),  # auto sem>=0.95 Bus Station / Terminal <-> Bus Station
    (197, 2043),  # auto sem>=0.95 Abortion Clinic <-> Urgent Care Clinic
    (198, 2043),  # auto sem>=0.95 Fertility Clinic <-> Urgent Care Clinic
    (202, 2328),  # auto sem>=0.95 Gynecologist <-> Emergency Medicine
    (216, 1853),  # auto sem>=0.95 LGBTQ+ Nightclub <-> Salsa Club
    (216, 2580),  # auto sem>=0.95 LGBTQ+ Nightclub <-> Club Crawl
    (266, 267),  # auto sem>=0.95 Radio Station <-> Television Station
    (273, 290),  # auto sem>=0.95 Parking Ticket Vending Machine <-> Transit Ticket Vending Machine
    (274, 275),  # auto sem>=0.95 Cigarette Vending Machine <-> Coffee Vending Machine
    (274, 287),  # auto sem>=0.95 Cigarette Vending Machine <-> Ice Vending Machine
    (275, 276),  # auto sem>=0.95 Coffee Vending Machine <-> Condom Vending Machine
    (275, 278),  # auto sem>=0.95 Coffee Vending Machine <-> Egg Vending Machine
    (275, 284),  # auto sem>=0.95 Coffee Vending Machine <-> Food Vending Machine
    (275, 286),  # auto sem>=0.95 Coffee Vending Machine <-> Ice Cream Vending Machine
    (275, 287),  # auto sem>=0.95 Coffee Vending Machine <-> Ice Vending Machine
    (275, 291),  # auto sem>=0.95 Coffee Vending Machine <-> Postage Vending Machine
    (276, 280),  # auto sem>=0.95 Condom Vending Machine <-> Flat Coin Vending Machine
    (276, 284),  # auto sem>=0.95 Condom Vending Machine <-> Food Vending Machine
    (276, 287),  # auto sem>=0.95 Condom Vending Machine <-> Ice Vending Machine
    (277, 278),  # auto sem>=0.95 Drink Vending Machine <-> Egg Vending Machine
    (277, 284),  # auto sem>=0.95 Drink Vending Machine <-> Food Vending Machine
    (277, 287),  # auto sem>=0.95 Drink Vending Machine <-> Ice Vending Machine
    (277, 289),  # auto sem>=0.95 Drink Vending Machine <-> Pizza Vending Machine
    (277, 292),  # auto sem>=0.95 Drink Vending Machine <-> Snack Vending Machine
    (278, 284),  # auto sem>=0.95 Egg Vending Machine <-> Food Vending Machine
    (278, 287),  # auto sem>=0.95 Egg Vending Machine <-> Ice Vending Machine
    (278, 289),  # auto sem>=0.95 Egg Vending Machine <-> Pizza Vending Machine
    (278, 291),  # auto sem>=0.95 Egg Vending Machine <-> Postage Vending Machine
    (278, 292),  # auto sem>=0.95 Egg Vending Machine <-> Snack Vending Machine
    (280, 284),  # auto sem>=0.95 Flat Coin Vending Machine <-> Food Vending Machine
    (284, 287),  # auto sem>=0.95 Food Vending Machine <-> Ice Vending Machine
    (286, 287),  # auto sem>=0.95 Ice Cream Vending Machine <-> Ice Vending Machine
    (287, 289),  # auto sem>=0.95 Ice Vending Machine <-> Pizza Vending Machine
    (287, 291),  # auto sem>=0.95 Ice Vending Machine <-> Postage Vending Machine
    (287, 292),  # auto sem>=0.95 Ice Vending Machine <-> Snack Vending Machine
    (289, 291),  # auto sem>=0.95 Pizza Vending Machine <-> Postage Vending Machine
    (289, 292),  # auto sem>=0.95 Pizza Vending Machine <-> Snack Vending Machine
    (291, 292),  # auto sem>=0.95 Postage Vending Machine <-> Snack Vending Machine
    (298, 299),  # auto sem>=0.95 E-Waste Container <-> Green Waste Container
    (416, 2102),  # auto sem>=0.95 Sports Club <-> Surf Lifesaving Club
    (497, 1721),  # auto sem>=0.95 Emergency Room Entrance <-> Emergency Room
    (514, 1828),  # auto sem>=0.95 Audiologist <-> Radiologist
    (517, 1808),  # auto sem>=0.95 Counselling Center <-> Abuse and Addiction Treatment
    (519, 2051),  # auto sem>=0.95 Medical Laboratory <-> Hematology
    (519, 2076),  # auto sem>=0.95 Medical Laboratory <-> Paternity Tests and Services
    (519, 2541),  # auto sem>=0.95 Medical Laboratory <-> Dental Laboratories
    (521, 1692),  # auto sem>=0.95 Occupational Therapist <-> Occupational Therapy
    (525, 1914),  # auto sem>=0.95 Psychotherapist <-> Sports Psychologist
    (526, 2040),  # auto sem>=0.95 Rehabilitation Facility <-> Addiction Rehabilitation Center
    (555, 606),  # auto sem>=0.95 Motorsport Racetrack <-> Motocross Racetrack
    (581, 2660),  # auto sem>=0.95 Crosswalk with Signals <-> Crosswalk with Signals
    (582, 597),  # auto sem>=0.95 Unmarked Crosswalk <-> Unmarked Crossing
    (589, 616),  # auto sem>=0.95 Cycle Crossing <-> Cycle & Foot Crossing
    (597, 618),  # auto sem>=0.95 Unmarked Crossing <-> Unmarked Cycle Crossing
    (605, 606),  # auto sem>=0.95 Karting Racetrack <-> Motocross Racetrack
    (615, 626),  # auto sem>=0.95 Commemorative Plaque <-> Memorial
    (615, 2644),  # auto sem>=0.95 Commemorative Plaque <-> Memorial Statue
    (622, 632),  # auto sem>=0.95 Castle <-> Historic Fortress
    (622, 633),  # auto sem>=0.95 Castle <-> Palace
    (622, 634),  # auto sem>=0.95 Castle <-> ChÃ¢teau
    (626, 2644),  # auto sem>=0.95 Memorial <-> Memorial Statue
    (632, 633),  # auto sem>=0.95 Historic Fortress <-> Palace
    (632, 634),  # auto sem>=0.95 Historic Fortress <-> ChÃ¢teau
    (633, 634),  # auto sem>=0.95 Palace <-> ChÃ¢teau
    (702, 732),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Balance Beam
    (702, 733),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Box
    (702, 734),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Horizontal Bar
    (702, 735),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Monkey Bars
    (702, 736),  # auto sem>=0.95 Outdoor Fitness Station <-> Hyperextension Station
    (702, 737),  # auto sem>=0.95 Outdoor Fitness Station <-> Parallel Bars
    (702, 738),  # auto sem>=0.95 Outdoor Fitness Station <-> Push-Up Station
    (702, 739),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Rings
    (702, 740),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Instruction Sign
    (702, 741),  # auto sem>=0.95 Outdoor Fitness Station <-> Sit-Up Station
    (702, 742),  # auto sem>=0.95 Outdoor Fitness Station <-> Exercise Stairs
    (717, 2102),  # auto sem>=0.95 Sports Club and League <-> Surf Lifesaving Club
    (732, 733),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Box
    (732, 734),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Horizontal Bar
    (732, 735),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Monkey Bars
    (732, 736),  # auto sem>=0.95 Exercise Balance Beam <-> Hyperextension Station
    (732, 737),  # auto sem>=0.95 Exercise Balance Beam <-> Parallel Bars
    (732, 738),  # auto sem>=0.95 Exercise Balance Beam <-> Push-Up Station
    (732, 739),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Rings
    (732, 740),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Instruction Sign
    (732, 741),  # auto sem>=0.95 Exercise Balance Beam <-> Sit-Up Station
    (732, 742),  # auto sem>=0.95 Exercise Balance Beam <-> Exercise Stairs
    (733, 734),  # auto sem>=0.95 Exercise Box <-> Exercise Horizontal Bar
    (733, 735),  # auto sem>=0.95 Exercise Box <-> Exercise Monkey Bars
    (733, 736),  # auto sem>=0.95 Exercise Box <-> Hyperextension Station
    (733, 737),  # auto sem>=0.95 Exercise Box <-> Parallel Bars
    (733, 738),  # auto sem>=0.95 Exercise Box <-> Push-Up Station
    (733, 739),  # auto sem>=0.95 Exercise Box <-> Exercise Rings
    (733, 740),  # auto sem>=0.95 Exercise Box <-> Exercise Instruction Sign
    (733, 741),  # auto sem>=0.95 Exercise Box <-> Sit-Up Station
    (733, 742),  # auto sem>=0.95 Exercise Box <-> Exercise Stairs
    (734, 735),  # auto sem>=0.95 Exercise Horizontal Bar <-> Exercise Monkey Bars
    (734, 736),  # auto sem>=0.95 Exercise Horizontal Bar <-> Hyperextension Station
    (734, 737),  # auto sem>=0.95 Exercise Horizontal Bar <-> Parallel Bars
    (734, 738),  # auto sem>=0.95 Exercise Horizontal Bar <-> Push-Up Station
    (734, 739),  # auto sem>=0.95 Exercise Horizontal Bar <-> Exercise Rings
    (734, 740),  # auto sem>=0.95 Exercise Horizontal Bar <-> Exercise Instruction Sign
    (734, 741),  # auto sem>=0.95 Exercise Horizontal Bar <-> Sit-Up Station
    (734, 742),  # auto sem>=0.95 Exercise Horizontal Bar <-> Exercise Stairs
    (735, 736),  # auto sem>=0.95 Exercise Monkey Bars <-> Hyperextension Station
    (735, 737),  # auto sem>=0.95 Exercise Monkey Bars <-> Parallel Bars
    (735, 738),  # auto sem>=0.95 Exercise Monkey Bars <-> Push-Up Station
    (735, 739),  # auto sem>=0.95 Exercise Monkey Bars <-> Exercise Rings
    (735, 740),  # auto sem>=0.95 Exercise Monkey Bars <-> Exercise Instruction Sign
    (735, 741),  # auto sem>=0.95 Exercise Monkey Bars <-> Sit-Up Station
    (735, 742),  # auto sem>=0.95 Exercise Monkey Bars <-> Exercise Stairs
    (736, 737),  # auto sem>=0.95 Hyperextension Station <-> Parallel Bars
    (736, 738),  # auto sem>=0.95 Hyperextension Station <-> Push-Up Station
    (736, 739),  # auto sem>=0.95 Hyperextension Station <-> Exercise Rings
    (736, 740),  # auto sem>=0.95 Hyperextension Station <-> Exercise Instruction Sign
    (736, 741),  # auto sem>=0.95 Hyperextension Station <-> Sit-Up Station
    (736, 742),  # auto sem>=0.95 Hyperextension Station <-> Exercise Stairs
    (737, 738),  # auto sem>=0.95 Parallel Bars <-> Push-Up Station
    (737, 739),  # auto sem>=0.95 Parallel Bars <-> Exercise Rings
    (737, 740),  # auto sem>=0.95 Parallel Bars <-> Exercise Instruction Sign
    (737, 741),  # auto sem>=0.95 Parallel Bars <-> Sit-Up Station
    (737, 742),  # auto sem>=0.95 Parallel Bars <-> Exercise Stairs
    (738, 739),  # auto sem>=0.95 Push-Up Station <-> Exercise Rings
    (738, 740),  # auto sem>=0.95 Push-Up Station <-> Exercise Instruction Sign
    (738, 741),  # auto sem>=0.95 Push-Up Station <-> Sit-Up Station
    (738, 742),  # auto sem>=0.95 Push-Up Station <-> Exercise Stairs
    (739, 740),  # auto sem>=0.95 Exercise Rings <-> Exercise Instruction Sign
    (739, 741),  # auto sem>=0.95 Exercise Rings <-> Sit-Up Station
    (739, 742),  # auto sem>=0.95 Exercise Rings <-> Exercise Stairs
    (740, 741),  # auto sem>=0.95 Exercise Instruction Sign <-> Sit-Up Station
    (740, 742),  # auto sem>=0.95 Exercise Instruction Sign <-> Exercise Stairs
    (741, 742),  # auto sem>=0.95 Sit-Up Station <-> Exercise Stairs
    (783, 785),  # auto sem>=0.95 Cycling Track <-> Horse Racetrack
    (783, 786),  # auto sem>=0.95 Cycling Track <-> Running Track
    (783, 2050),  # auto sem>=0.95 Cycling Track <-> Mountain Bike Parks
    (785, 786),  # auto sem>=0.95 Horse Racetrack <-> Running Track
    (785, 2050),  # auto sem>=0.95 Horse Racetrack <-> Mountain Bike Parks
    (786, 2050),  # auto sem>=0.95 Running Track <-> Mountain Bike Parks
    (813, 1832),  # auto sem>=0.95 Monitoring Station <-> Weather Station
    (988, 1497),  # auto sem>=0.95 Square <-> Public Plaza
    (1419, 2043),  # auto sem>=0.95 Prenatal Perinatal Care <-> Urgent Care Clinic
    (1423, 2043),  # auto sem>=0.95 Family Practice <-> Urgent Care Clinic
    (1437, 2545),  # auto sem>=0.95 Martial Arts Club <-> Karate Club
    (1461, 2043),  # auto sem>=0.95 Cannabis Clinic <-> Urgent Care Clinic
    (1486, 1669),  # auto sem>=0.95 Vocational and Technical School <-> Cooking School
    (1486, 1875),  # auto sem>=0.95 Vocational and Technical School <-> Bartender
    (1486, 1932),  # auto sem>=0.95 Vocational and Technical School <-> Massage School
    (1486, 2037),  # auto sem>=0.95 Vocational and Technical School <-> Cooking Classes
    (1486, 2542),  # auto sem>=0.95 Vocational and Technical School <-> Drama School
    (1488, 2043),  # auto sem>=0.95 Alcohol and Drug Treatment Centers <-> Urgent Care Clinic
    (1493, 1531),  # auto sem>=0.95 Business Manufacturing and Supply <-> Plastic Manufacturer
    (1501, 2043),  # auto sem>=0.95 Home Health Care <-> Urgent Care Clinic
    (1508, 2043),  # auto sem>=0.95 Diagnostic Services <-> Urgent Care Clinic
    (1531, 1693),  # auto sem>=0.95 Plastic Manufacturer <-> Glass Manufacturer
    (1565, 2043),  # auto sem>=0.95 Eye Care Clinic <-> Urgent Care Clinic
    (1566, 1568),  # auto sem>=0.95 Boxing Class <-> Ski and Snowboard School
    (1566, 1750),  # auto sem>=0.95 Boxing Class <-> Swimming Instructor
    (1566, 1782),  # auto sem>=0.95 Boxing Class <-> Sports and Fitness Instruction
    (1566, 1799),  # auto sem>=0.95 Boxing Class <-> Sky Diving
    (1566, 1827),  # auto sem>=0.95 Boxing Class <-> Cycling Classes
    (1566, 1836),  # auto sem>=0.95 Boxing Class <-> Scuba Diving Instruction
    (1566, 1868),  # auto sem>=0.95 Boxing Class <-> Golf Instructor
    (1566, 2060),  # auto sem>=0.95 Boxing Class <-> Surfing School
    (1566, 2074),  # auto sem>=0.95 Boxing Class <-> Kiteboarding Instruction
    (1566, 2186),  # auto sem>=0.95 Boxing Class <-> Parasailing Ride Service
    (1566, 2239),  # auto sem>=0.95 Boxing Class <-> Yoga Instructor
    (1566, 2344),  # auto sem>=0.95 Boxing Class <-> Self Defense Classes
    (1566, 2414),  # auto sem>=0.95 Boxing Class <-> Rock Climbing Instructor
    (1566, 2442),  # auto sem>=0.95 Boxing Class <-> Paddleboarding Lessons
    (1566, 2444),  # auto sem>=0.95 Boxing Class <-> Climbing Class
    (1566, 2670),  # auto sem>=0.95 Boxing Class <-> Ski School
    (1568, 1750),  # auto sem>=0.95 Ski and Snowboard School <-> Swimming Instructor
    (1568, 1782),  # auto sem>=0.95 Ski and Snowboard School <-> Sports and Fitness Instruction
    (1568, 1799),  # auto sem>=0.95 Ski and Snowboard School <-> Sky Diving
    (1568, 1827),  # auto sem>=0.95 Ski and Snowboard School <-> Cycling Classes
    (1568, 1836),  # auto sem>=0.95 Ski and Snowboard School <-> Scuba Diving Instruction
    (1568, 1868),  # auto sem>=0.95 Ski and Snowboard School <-> Golf Instructor
    (1568, 2060),  # auto sem>=0.95 Ski and Snowboard School <-> Surfing School
    (1568, 2074),  # auto sem>=0.95 Ski and Snowboard School <-> Kiteboarding Instruction
    (1568, 2186),  # auto sem>=0.95 Ski and Snowboard School <-> Parasailing Ride Service
    (1568, 2239),  # auto sem>=0.95 Ski and Snowboard School <-> Yoga Instructor
    (1568, 2344),  # auto sem>=0.95 Ski and Snowboard School <-> Self Defense Classes
    (1568, 2414),  # auto sem>=0.95 Ski and Snowboard School <-> Rock Climbing Instructor
    (1568, 2442),  # auto sem>=0.95 Ski and Snowboard School <-> Paddleboarding Lessons
    (1568, 2444),  # auto sem>=0.95 Ski and Snowboard School <-> Climbing Class
    (1568, 2670),  # auto sem>=0.95 Ski and Snowboard School <-> Ski School
    (1575, 1853),  # auto sem>=0.95 Jazz and Blues <-> Salsa Club
    (1591, 2043),  # auto sem>=0.95 Fertility <-> Urgent Care Clinic
    (1630, 2043),  # auto sem>=0.95 Maternity Centers <-> Urgent Care Clinic
    (1640, 2043),  # auto sem>=0.95 Weight Loss Center <-> Urgent Care Clinic
    (1669, 1875),  # auto sem>=0.95 Cooking School <-> Bartender
    (1669, 1932),  # auto sem>=0.95 Cooking School <-> Massage School
    (1669, 2037),  # auto sem>=0.95 Cooking School <-> Cooking Classes
    (1669, 2542),  # auto sem>=0.95 Cooking School <-> Drama School
    (1750, 1782),  # auto sem>=0.95 Swimming Instructor <-> Sports and Fitness Instruction
    (1750, 1799),  # auto sem>=0.95 Swimming Instructor <-> Sky Diving
    (1750, 1827),  # auto sem>=0.95 Swimming Instructor <-> Cycling Classes
    (1750, 1836),  # auto sem>=0.95 Swimming Instructor <-> Scuba Diving Instruction
    (1750, 1868),  # auto sem>=0.95 Swimming Instructor <-> Golf Instructor
    (1750, 2060),  # auto sem>=0.95 Swimming Instructor <-> Surfing School
    (1750, 2074),  # auto sem>=0.95 Swimming Instructor <-> Kiteboarding Instruction
    (1750, 2186),  # auto sem>=0.95 Swimming Instructor <-> Parasailing Ride Service
    (1750, 2239),  # auto sem>=0.95 Swimming Instructor <-> Yoga Instructor
    (1750, 2344),  # auto sem>=0.95 Swimming Instructor <-> Self Defense Classes
    (1750, 2414),  # auto sem>=0.95 Swimming Instructor <-> Rock Climbing Instructor
    (1750, 2442),  # auto sem>=0.95 Swimming Instructor <-> Paddleboarding Lessons
    (1750, 2444),  # auto sem>=0.95 Swimming Instructor <-> Climbing Class
    (1750, 2670),  # auto sem>=0.95 Swimming Instructor <-> Ski School
    (1754, 2328),  # auto sem>=0.95 Surgeon <-> Emergency Medicine
    (1762, 2043),  # auto sem>=0.95 Women's Health Clinic <-> Urgent Care Clinic
    (1782, 1799),  # auto sem>=0.95 Sports and Fitness Instruction <-> Sky Diving
    (1782, 1827),  # auto sem>=0.95 Sports and Fitness Instruction <-> Cycling Classes
    (1782, 1836),  # auto sem>=0.95 Sports and Fitness Instruction <-> Scuba Diving Instruction
    (1782, 1868),  # auto sem>=0.95 Sports and Fitness Instruction <-> Golf Instructor
    (1782, 2060),  # auto sem>=0.95 Sports and Fitness Instruction <-> Surfing School
    (1782, 2074),  # auto sem>=0.95 Sports and Fitness Instruction <-> Kiteboarding Instruction
    (1782, 2186),  # auto sem>=0.95 Sports and Fitness Instruction <-> Parasailing Ride Service
    (1782, 2239),  # auto sem>=0.95 Sports and Fitness Instruction <-> Yoga Instructor
    (1782, 2344),  # auto sem>=0.95 Sports and Fitness Instruction <-> Self Defense Classes
    (1782, 2414),  # auto sem>=0.95 Sports and Fitness Instruction <-> Rock Climbing Instructor
    (1782, 2442),  # auto sem>=0.95 Sports and Fitness Instruction <-> Paddleboarding Lessons
    (1782, 2444),  # auto sem>=0.95 Sports and Fitness Instruction <-> Climbing Class
    (1782, 2670),  # auto sem>=0.95 Sports and Fitness Instruction <-> Ski School
    (1799, 1827),  # auto sem>=0.95 Sky Diving <-> Cycling Classes
    (1799, 1836),  # auto sem>=0.95 Sky Diving <-> Scuba Diving Instruction
    (1799, 1868),  # auto sem>=0.95 Sky Diving <-> Golf Instructor
    (1799, 2060),  # auto sem>=0.95 Sky Diving <-> Surfing School
    (1799, 2074),  # auto sem>=0.95 Sky Diving <-> Kiteboarding Instruction
    (1799, 2186),  # auto sem>=0.95 Sky Diving <-> Parasailing Ride Service
    (1799, 2239),  # auto sem>=0.95 Sky Diving <-> Yoga Instructor
    (1799, 2344),  # auto sem>=0.95 Sky Diving <-> Self Defense Classes
    (1799, 2414),  # auto sem>=0.95 Sky Diving <-> Rock Climbing Instructor
    (1799, 2442),  # auto sem>=0.95 Sky Diving <-> Paddleboarding Lessons
    (1799, 2444),  # auto sem>=0.95 Sky Diving <-> Climbing Class
    (1799, 2670),  # auto sem>=0.95 Sky Diving <-> Ski School
    (1808, 2296),  # auto sem>=0.95 Abuse and Addiction Treatment <-> Suicide Prevention Services
    (1827, 1836),  # auto sem>=0.95 Cycling Classes <-> Scuba Diving Instruction
    (1827, 1868),  # auto sem>=0.95 Cycling Classes <-> Golf Instructor
    (1827, 2060),  # auto sem>=0.95 Cycling Classes <-> Surfing School
    (1827, 2074),  # auto sem>=0.95 Cycling Classes <-> Kiteboarding Instruction
    (1827, 2186),  # auto sem>=0.95 Cycling Classes <-> Parasailing Ride Service
    (1827, 2239),  # auto sem>=0.95 Cycling Classes <-> Yoga Instructor
    (1827, 2344),  # auto sem>=0.95 Cycling Classes <-> Self Defense Classes
    (1827, 2414),  # auto sem>=0.95 Cycling Classes <-> Rock Climbing Instructor
    (1827, 2442),  # auto sem>=0.95 Cycling Classes <-> Paddleboarding Lessons
    (1827, 2444),  # auto sem>=0.95 Cycling Classes <-> Climbing Class
    (1827, 2670),  # auto sem>=0.95 Cycling Classes <-> Ski School
    (1836, 1868),  # auto sem>=0.95 Scuba Diving Instruction <-> Golf Instructor
    (1836, 2060),  # auto sem>=0.95 Scuba Diving Instruction <-> Surfing School
    (1836, 2074),  # auto sem>=0.95 Scuba Diving Instruction <-> Kiteboarding Instruction
    (1836, 2186),  # auto sem>=0.95 Scuba Diving Instruction <-> Parasailing Ride Service
    (1836, 2239),  # auto sem>=0.95 Scuba Diving Instruction <-> Yoga Instructor
    (1836, 2344),  # auto sem>=0.95 Scuba Diving Instruction <-> Self Defense Classes
    (1836, 2414),  # auto sem>=0.95 Scuba Diving Instruction <-> Rock Climbing Instructor
    (1836, 2442),  # auto sem>=0.95 Scuba Diving Instruction <-> Paddleboarding Lessons
    (1836, 2444),  # auto sem>=0.95 Scuba Diving Instruction <-> Climbing Class
    (1836, 2670),  # auto sem>=0.95 Scuba Diving Instruction <-> Ski School
    (1853, 2580),  # auto sem>=0.95 Salsa Club <-> Club Crawl
    (1858, 2543),  # auto sem>=0.95 Oil Change Station <-> Truck Gas Station
    (1868, 2060),  # auto sem>=0.95 Golf Instructor <-> Surfing School
    (1868, 2074),  # auto sem>=0.95 Golf Instructor <-> Kiteboarding Instruction
    (1868, 2186),  # auto sem>=0.95 Golf Instructor <-> Parasailing Ride Service
    (1868, 2239),  # auto sem>=0.95 Golf Instructor <-> Yoga Instructor
    (1868, 2344),  # auto sem>=0.95 Golf Instructor <-> Self Defense Classes
    (1868, 2414),  # auto sem>=0.95 Golf Instructor <-> Rock Climbing Instructor
    (1868, 2442),  # auto sem>=0.95 Golf Instructor <-> Paddleboarding Lessons
    (1868, 2444),  # auto sem>=0.95 Golf Instructor <-> Climbing Class
    (1868, 2670),  # auto sem>=0.95 Golf Instructor <-> Ski School
    (1873, 2043),  # auto sem>=0.95 Dialysis Clinic <-> Urgent Care Clinic
    (1875, 1932),  # auto sem>=0.95 Bartender <-> Massage School
    (1875, 2037),  # auto sem>=0.95 Bartender <-> Cooking Classes
    (1875, 2542),  # auto sem>=0.95 Bartender <-> Drama School
    (1901, 2147),  # auto sem>=0.95 Emergency Roadside Service <-> Roadside Assistance
    (1932, 2037),  # auto sem>=0.95 Massage School <-> Cooking Classes
    (1932, 2542),  # auto sem>=0.95 Massage School <-> Drama School
    (2023, 2303),  # auto sem>=0.95 Environmental Testing <-> Laboratory
    (2033, 2564),  # auto sem>=0.95 Adult Education <-> Circus School
    (2037, 2542),  # auto sem>=0.95 Cooking Classes <-> Drama School
    (2043, 2534),  # auto sem>=0.95 Urgent Care Clinic <-> Cancer Treatment Center
    (2051, 2076),  # auto sem>=0.95 Hematology <-> Paternity Tests and Services
    (2051, 2541),  # auto sem>=0.95 Hematology <-> Dental Laboratories
    (2060, 2074),  # auto sem>=0.95 Surfing School <-> Kiteboarding Instruction
    (2060, 2186),  # auto sem>=0.95 Surfing School <-> Parasailing Ride Service
    (2060, 2239),  # auto sem>=0.95 Surfing School <-> Yoga Instructor
    (2060, 2344),  # auto sem>=0.95 Surfing School <-> Self Defense Classes
    (2060, 2414),  # auto sem>=0.95 Surfing School <-> Rock Climbing Instructor
    (2060, 2442),  # auto sem>=0.95 Surfing School <-> Paddleboarding Lessons
    (2060, 2444),  # auto sem>=0.95 Surfing School <-> Climbing Class
    (2060, 2670),  # auto sem>=0.95 Surfing School <-> Ski School
    (2074, 2186),  # auto sem>=0.95 Kiteboarding Instruction <-> Parasailing Ride Service
    (2074, 2239),  # auto sem>=0.95 Kiteboarding Instruction <-> Yoga Instructor
    (2074, 2344),  # auto sem>=0.95 Kiteboarding Instruction <-> Self Defense Classes
    (2074, 2414),  # auto sem>=0.95 Kiteboarding Instruction <-> Rock Climbing Instructor
    (2074, 2442),  # auto sem>=0.95 Kiteboarding Instruction <-> Paddleboarding Lessons
    (2074, 2444),  # auto sem>=0.95 Kiteboarding Instruction <-> Climbing Class
    (2074, 2670),  # auto sem>=0.95 Kiteboarding Instruction <-> Ski School
    (2076, 2541),  # auto sem>=0.95 Paternity Tests and Services <-> Dental Laboratories
    (2089, 2626),  # auto sem>=0.95 Leather Products Manufacturer <-> Cosmetic Products Manufacturer
    (2102, 2356),  # auto sem>=0.95 Surf Lifesaving Club <-> Football Club
    (2102, 2373),  # auto sem>=0.95 Surf Lifesaving Club <-> Beach Volleyball Club
    (2102, 2514),  # auto sem>=0.95 Surf Lifesaving Club <-> Volleyball Club
    (2102, 2589),  # auto sem>=0.95 Surf Lifesaving Club <-> Rowing Club
    (2102, 2616),  # auto sem>=0.95 Surf Lifesaving Club <-> Taekwondo Club
    (2102, 2680),  # auto sem>=0.95 Surf Lifesaving Club <-> Billiards
    (2186, 2239),  # auto sem>=0.95 Parasailing Ride Service <-> Yoga Instructor
    (2186, 2344),  # auto sem>=0.95 Parasailing Ride Service <-> Self Defense Classes
    (2186, 2414),  # auto sem>=0.95 Parasailing Ride Service <-> Rock Climbing Instructor
    (2186, 2442),  # auto sem>=0.95 Parasailing Ride Service <-> Paddleboarding Lessons
    (2186, 2444),  # auto sem>=0.95 Parasailing Ride Service <-> Climbing Class
    (2186, 2670),  # auto sem>=0.95 Parasailing Ride Service <-> Ski School
    (2237, 2340),  # auto sem>=0.95 Child Psychiatrist <-> Geriatric Psychiatry
    (2239, 2344),  # auto sem>=0.95 Yoga Instructor <-> Self Defense Classes
    (2239, 2414),  # auto sem>=0.95 Yoga Instructor <-> Rock Climbing Instructor
    (2239, 2442),  # auto sem>=0.95 Yoga Instructor <-> Paddleboarding Lessons
    (2239, 2444),  # auto sem>=0.95 Yoga Instructor <-> Climbing Class
    (2239, 2670),  # auto sem>=0.95 Yoga Instructor <-> Ski School
    (2273, 2627),  # auto sem>=0.95 Halotherapy <-> Hydrotherapy
    (2328, 2446),  # auto sem>=0.95 Emergency Medicine <-> Diagnostic Imaging
    (2344, 2414),  # auto sem>=0.95 Self Defense Classes <-> Rock Climbing Instructor
    (2344, 2442),  # auto sem>=0.95 Self Defense Classes <-> Paddleboarding Lessons
    (2344, 2444),  # auto sem>=0.95 Self Defense Classes <-> Climbing Class
    (2344, 2670),  # auto sem>=0.95 Self Defense Classes <-> Ski School
    (2378, 2628),  # auto sem>=0.95 Emergency Pet Hospital <-> Animal Physical Therapy
    (2414, 2442),  # auto sem>=0.95 Rock Climbing Instructor <-> Paddleboarding Lessons
    (2414, 2444),  # auto sem>=0.95 Rock Climbing Instructor <-> Climbing Class
    (2414, 2670),  # auto sem>=0.95 Rock Climbing Instructor <-> Ski School
    (2442, 2444),  # auto sem>=0.95 Paddleboarding Lessons <-> Climbing Class
    (2442, 2670),  # auto sem>=0.95 Paddleboarding Lessons <-> Ski School
    (2444, 2670),  # auto sem>=0.95 Climbing Class <-> Ski School
    (112, 355),  # auto sem>=0.95 Preschool / Kindergarten Grounds <-> Preschool / Kindergarten Building
    (157, 1394),  # auto sem>=0.95 RV Toilet Disposal <-> Marine Toilet Disposal
    (188, 1405),  # auto sem>=0.95 Coworking Space <-> co-working space other
    (1536, 2623),  # auto sem>=0.95 Bar and Grill Restaurant <-> Brasserie
}


@dataclass(frozen=True)
class PresetInfo:
    pid: int
    name: str
    tags: Dict[str, str]
    geometry: List[str]
    overture_categories: List[str]

    @property
    def point_capable(self) -> bool:
        return "point" in self.geometry or "vertex" in self.geometry


@dataclass
class Semantic:
    families: Set[str]
    hard_block: bool


def norm_tags(raw: Dict[str, object]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (raw or {}).items():
        if k is None or v is None:
            continue
        ks = str(k).strip().lower()
        vs = str(v).strip().lower()
        if ks and vs:
            out[ks] = vs
    return out


def load_presets(path: Path) -> List[PresetInfo]:
    rows = json.loads(path.read_text())
    out: List[PresetInfo] = []
    for r in rows:
        out.append(
            PresetInfo(
                pid=int(r["id"]),
                name=str(r.get("name", "")),
                tags=norm_tags(r.get("tags", {})),
                geometry=[str(g).lower() for g in r.get("geometry", []) if g is not None],
                overture_categories=[str(x).strip().lower() for x in r.get("overture_categories", []) if x],
            )
        )
    return out


def tag(p: PresetInfo, key: str) -> str | None:
    return p.tags.get(key)


def classify(p: PresetInfo) -> Semantic:
    f: Set[str] = set()

    # Hard blocks first.
    if any(k in p.tags for k in BLOCK_KEYS):
        return Semantic(families={"non_place"}, hard_block=True)

    # Emergency equipment is non-place.
    em = tag(p, "emergency")
    if em in {"defibrillator", "fire_hydrant", "fire_alarm_box", "fire_extinguisher", "life_ring", "yes", "private", "official", "destination", "designated", "no"}:
        return Semantic(families={"non_place"}, hard_block=True)

    # Transport taxonomy.
    if any(k in p.tags for k in TRANSIT_KEYS):
        f.add("transit")
        pt = tag(p, "public_transport")
        rw = tag(p, "railway")
        aw = tag(p, "aerialway")
        if pt in {"platform", "stop_position", "stop_area", "station"}:
            f.add("transit_stop")
        if rw in {"station", "halt", "tram_stop", "subway_entrance", "platform"}:
            f.add("transit_stop")
        if aw:
            f.add("transit_lift")

    # Office.
    off = tag(p, "office")
    if off:
        f.add("office")
        if off in {"it", "software_development", "company", "consulting", "coworking", "telecommunication", "engineer", "architect"}:
            f.add("office_knowledge")
        if off in {"government", "administrative", "diplomatic", "ngo", "association"}:
            f.add("civic")
        if off in {"religious_organization"} or "religious" in off:
            f.add("religion")
        if off in {"bus_service", "transport", "travel_agent"}:
            f.add("transit_service")

    # Amenity.
    am = tag(p, "amenity")
    if am:
        if am in {"restaurant", "cafe", "fast_food", "bar", "pub", "biergarten", "food_court", "ice_cream"}:
            f.add("food_service")
        if am in {"school", "kindergarten", "college", "university", "library", "childcare"}:
            f.add("education")
        # Early childhood institutions are often mapped as kindergarten vs childcare.
        if am in {"kindergarten", "childcare"}:
            f.add("early_education")
        if am in {"hospital", "clinic", "doctors", "dentist", "pharmacy", "veterinary"}:
            f.add("health")
        if am in {"bank", "atm", "bureau_de_change"}:
            f.add("finance")
        if am in {"community_centre", "townhall", "courthouse", "post_office", "police", "fire_station", "social_facility"}:
            f.add("civic")
        # Library and social facility frequently represent the same municipal/community node.
        if am in {"library", "social_facility"}:
            f.add("community_learning")
        if am in {"arts_centre", "theatre", "cinema"}:
            f.add("culture")

    # Healthcare key family (covers presets like healthcare=alternative, healthcare:speciality=chiropractic).
    hc = tag(p, "healthcare")
    hcs = tag(p, "healthcare:speciality")
    if hc:
        if hc in {"hospital", "clinic", "doctor", "dentist", "pharmacy", "veterinary", "alternative"}:
            f.add("health")
    if hcs:
        if hcs in {"chiropractic", "chiropractor", "general", "dentistry", "physiotherapy"}:
            f.add("health")

    # Shop.
    sh = tag(p, "shop")
    if sh:
        f.add("retail")
        if sh in {"bakery", "deli", "butcher", "greengrocer", "convenience", "supermarket", "seafood", "beverages", "confectionery"}:
            f.add("food_retail")
        if sh in {"clothes", "shoes", "jewelry", "bag", "fashion_accessories", "beauty"}:
            f.add("retail_fashion")
        if sh in {"electronics", "computer", "mobile_phone", "hifi"}:
            f.add("retail_electronics")

    # Tourism.
    tr = tag(p, "tourism")
    if tr:
        if tr in {"hotel", "hostel", "motel", "guest_house", "apartment", "resort"}:
            f.add("lodging")
        if tr in {"museum", "gallery", "attraction", "viewpoint", "zoo", "aquarium", "theme_park"}:
            f.add("culture")

    # Leisure/sport.
    le = tag(p, "leisure")
    if le:
        if le in {"sports_centre", "stadium", "fitness_centre", "pitch", "golf_course", "swimming_pool", "bowling_alley"}:
            f.add("sports")
        if le in {"park", "garden", "nature_reserve"}:
            f.add("park")
    club = tag(p, "club")
    if club in {"sport", "sports"}:
        f.add("sports")

    # Religion.
    if tag(p, "amenity") == "place_of_worship":
        f.add("religion")

    # If unknown but point-like and named POI preset, keep generic place bucket.
    if not f:
        f.add("generic_place")

    return Semantic(families=f, hard_block=False)


def edge_score(pa: PresetInfo, sa: Semantic, pb: PresetInfo, sb: Semantic) -> float:
    if pa.pid == pb.pid:
        return 1.0

    if (pa.pid, pb.pid) in FORCED_ALLOW_PAIRS or (pb.pid, pa.pid) in FORCED_ALLOW_PAIRS:
        return 0.95

    # Hard blocks: default no, unless exact same key/value tags (already handled above by pid in practice).
    if sa.hard_block or sb.hard_block:
        return 0.0

    # Exact same tag dict is strong (duplicate taxonomy split across ids).
    if pa.tags and pa.tags == pb.tags:
        return 0.98

    # Never merge transit with non-transit unless both transit families present.
    a_transit = "transit" in sa.families or "transit_service" in sa.families
    b_transit = "transit" in sb.families or "transit_service" in sb.families
    if a_transit != b_transit:
        return 0.0

    common = sa.families.intersection(sb.families)
    if common:
        # Same high-confidence family.
        if any(x in common for x in {"office_knowledge", "food_service", "food_retail", "lodging", "education", "early_education", "community_learning", "health", "culture", "sports", "park", "religion", "transit_stop", "transit_lift"}):
            return 0.92
        # Generic common family.
        if any(x in common for x in {"office", "retail", "finance", "civic", "transit", "transit_service"}):
            return 0.84

    # Cross-family allowances for common messy map taxonomy drift.
    # Food service vs food retail often represent same storefront with different tagging.
    if ({"food_service", "food_retail"}.issubset(sa.families.union(sb.families))):
        return 0.82

    # Culture/education overlap (arts schools, museum-education complexes) - weaker.
    if ({"culture", "education"}.issubset(sa.families.union(sb.families))):
        return 0.76

    # Office knowledge vs retail (e.g. showroom) should not auto-merge.
    return 0.0


def build_graph(presets: List[PresetInfo], threshold: float, all_geometries: bool) -> Tuple[Dict[str, List[int]], Dict[str, Dict[str, object]]]:
    scope = presets if all_geometries else [p for p in presets if p.point_capable]
    sem = {p.pid: classify(p) for p in presets}

    graph: Dict[str, List[int]] = {str(p.pid): [p.pid] for p in presets}  # self-edge always
    meta: Dict[str, Dict[str, object]] = {}

    for p in presets:
        s = sem[p.pid]
        meta[str(p.pid)] = {
            "name": p.name,
            "families": sorted(s.families),
            "hard_block": s.hard_block,
            "point_capable": p.point_capable,
            "tags": p.tags,
        }

    for a in scope:
        out: List[Tuple[int, float]] = [(a.pid, 1.0)]
        sa = sem[a.pid]
        for b in scope:
            if a.pid == b.pid:
                continue
            sb = sem[b.pid]
            s = edge_score(a, sa, b, sb)
            if s >= threshold:
                out.append((b.pid, s))
        out.sort(key=lambda t: (-t[1], t[0]))
        graph[str(a.pid)] = [pid for pid, _ in out]

    return graph, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Build preset compatibility graph")
    parser.add_argument("--presets", default="meta/presets.json")
    parser.add_argument("--out", default="meta/poi_preset_compat_graph_v1.json")
    parser.add_argument("--out-meta", default="meta/poi_preset_compat_graph_v1_meta.json")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--all-geometries", action="store_true", help="Compute edges for all preset geometries, not only point/vertex")
    args = parser.parse_args()

    presets = load_presets(Path(args.presets))
    graph, meta = build_graph(presets, threshold=args.threshold, all_geometries=args.all_geometries)

    output = {
        "version": 1,
        "kind": "preset_compatibility_graph",
        "model": "taxonomy_pairwise_allowlist",
        "threshold": args.threshold,
        "all_geometries": bool(args.all_geometries),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": args.presets,
        "preset_count": len(presets),
        "node_count": len(graph),
        "graph": graph,
    }

    Path(args.out).write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    Path(args.out_meta).write_text(json.dumps({"version": 1, "meta": meta}, ensure_ascii=False, separators=(",", ":"), sort_keys=True))

    print(f"Wrote {args.out}")
    print(f"Wrote {args.out_meta}")
    print(f"Nodes: {len(graph)}")


if __name__ == "__main__":
    main()
