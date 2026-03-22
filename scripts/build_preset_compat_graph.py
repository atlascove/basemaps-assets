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
    (56, 57),  # auto sem-all Animal Boarding Facility <-> Animal Breeding Facility
    (261, 1976),  # auto sem-all Food Bank <-> Food Banks
    (383, 384),  # auto sem-all Garage <-> Garages
    (427, 1886),  # auto sem-all Chimney Sweeper <-> Chimney Sweep
    (617, 618),  # auto sem-all Marked Cycle Crossing <-> Unmarked Cycle Crossing
    (235, 2623),  # auto sem-all American Restaurant <-> Brasserie
    (236, 2623),  # auto sem-all Asian Restaurant <-> Brasserie
    (237, 2623),  # auto sem-all Chinese Restaurant <-> Brasserie
    (238, 2623),  # auto sem-all French Restaurant <-> Brasserie
    (239, 2623),  # auto sem-all German Restaurant <-> Brasserie
    (240, 2623),  # auto sem-all Greek Restaurant <-> Brasserie
    (241, 2623),  # auto sem-all Indian Restaurant <-> Brasserie
    (242, 2623),  # auto sem-all Italian Restaurant <-> Brasserie
    (243, 2623),  # auto sem-all Japanese Restaurant <-> Brasserie
    (244, 2623),  # auto sem-all Mexican Restaurant <-> Brasserie
    (245, 2623),  # auto sem-all Noodle Restaurant <-> Brasserie
    (247, 2623),  # auto sem-all Pizza Restaurant <-> Brasserie
    (248, 2623),  # auto sem-all Seafood Restaurant <-> Brasserie
    (249, 2623),  # auto sem-all Steakhouse <-> Brasserie
    (251, 2623),  # auto sem-all Sushi Restaurant <-> Brasserie
    (252, 2623),  # auto sem-all Thai Restaurant <-> Brasserie
    (253, 2623),  # auto sem-all Turkish Restaurant <-> Brasserie
    (254, 2623),  # auto sem-all Vietnamese Restaurant <-> Brasserie
    (1404, 2623),  # auto sem-all Korean Restaurant <-> Brasserie
    (1440, 2623),  # auto sem-all Cajun Creole Restaurant <-> Brasserie
    (1444, 2623),  # auto sem-all Diner <-> Brasserie
    (1447, 2623),  # auto sem-all Lebanese Restaurant <-> Brasserie
    (1451, 2623),  # auto sem-all Mediterranean Restaurant <-> Brasserie
    (1460, 2623),  # auto sem-all Buffet Restaurant <-> Brasserie
    (1462, 2623),  # auto sem-all Burger Restaurant <-> Brasserie
    (1490, 2623),  # auto sem-all Barbecue Restaurant <-> Brasserie
    (1499, 2623),  # auto sem-all Fish and Chips Restaurant <-> Brasserie
    (1504, 2623),  # auto sem-all Desserts <-> Brasserie
    (1505, 2623),  # auto sem-all Chicken Restaurant <-> Brasserie
    (1511, 2623),  # auto sem-all Indonesian Restaurant <-> Brasserie
    (1524, 2623),  # auto sem-all Argentine Restaurant <-> Brasserie
    (1529, 2623),  # auto sem-all Breakfast and Brunch Restaurant <-> Brasserie
    (1533, 2623),  # auto sem-all Brazilian Restaurant <-> Brasserie
    (1539, 2623),  # auto sem-all Bolivian Restaurant <-> Brasserie
    (1546, 2623),  # auto sem-all Fondue Restaurant <-> Brasserie
    (1561, 2623),  # auto sem-all Soul Food <-> Brasserie
    (1572, 2623),  # auto sem-all European Restaurant <-> Brasserie
    (1577, 2623),  # auto sem-all Noodles Restaurant <-> Brasserie
    (1584, 2623),  # auto sem-all Latin American Restaurant <-> Brasserie
    (1593, 2623),  # auto sem-all Filipino Restaurant <-> Brasserie
    (1609, 2623),  # auto sem-all Persian Restaurant <-> Brasserie
    (1617, 2623),  # auto sem-all Soup Restaurant <-> Brasserie
    (1620, 2623),  # auto sem-all Spanish Restaurant <-> Brasserie
    (1622, 2623),  # auto sem-all Dim Sum Restaurant <-> Brasserie
    (1648, 2623),  # auto sem-all Middle Eastern Restaurant <-> Brasserie
    (1649, 2623),  # auto sem-all Russian Restaurant <-> Brasserie
    (1658, 2623),  # auto sem-all Kosher Restaurant <-> Brasserie
    (1659, 2623),  # auto sem-all Taiwanese Restaurant <-> Brasserie
    (1660, 2623),  # auto sem-all Eastern European Restaurant <-> Brasserie
    (1666, 2623),  # auto sem-all Ukrainian Restaurant <-> Brasserie
    (1668, 2623),  # auto sem-all African Restaurant <-> Brasserie
    (1676, 2623),  # auto sem-all Burmese Restaurant <-> Brasserie
    (1679, 2623),  # auto sem-all Comfort Food Restaurant <-> Brasserie
    (1680, 2623),  # auto sem-all Halal Restaurant <-> Brasserie
    (1698, 2623),  # auto sem-all Hot Dog Restaurant <-> Brasserie
    (1699, 2623),  # auto sem-all Moroccan Restaurant <-> Brasserie
    (1713, 2623),  # auto sem-all South African Restaurant <-> Brasserie
    (1722, 2623),  # auto sem-all Malaysian Restaurant <-> Brasserie
    (1723, 2623),  # auto sem-all Arabian Restaurant <-> Brasserie
    (1743, 2623),  # auto sem-all Pakistani Restaurant <-> Brasserie
    (1746, 2623),  # auto sem-all Polish Restaurant <-> Brasserie
    (1751, 2623),  # auto sem-all Doner Kebab <-> Brasserie
    (1757, 2623),  # auto sem-all Hungarian Restaurant <-> Brasserie
    (1758, 2623),  # auto sem-all Poke <-> Brasserie
    (1759, 2623),  # auto sem-all Southern Restaurant <-> Brasserie
    (1763, 2623),  # auto sem-all Salvadoran Restaurant <-> Brasserie
    (1771, 2623),  # auto sem-all Hawaiian Restaurant <-> Brasserie
    (1772, 2623),  # auto sem-all Australian Restaurant <-> Brasserie
    (1778, 2623),  # auto sem-all Peruvian Restaurant <-> Brasserie
    (1780, 2623),  # auto sem-all Cambodian Restaurant <-> Brasserie
    (1784, 2623),  # auto sem-all Caribbean Restaurant <-> Brasserie
    (1787, 2623),  # auto sem-all Portuguese Restaurant <-> Brasserie
    (1791, 2623),  # auto sem-all Live and Raw Food Restaurant <-> Brasserie
    (1796, 2623),  # auto sem-all British Restaurant <-> Brasserie
    (1803, 2623),  # auto sem-all Scandinavian Restaurant <-> Brasserie
    (1809, 2623),  # auto sem-all Trinidadian Restaurant <-> Brasserie
    (1817, 2623),  # auto sem-all Panamanian Restaurant <-> Brasserie
    (1819, 2623),  # auto sem-all Himalayan Nepalese Restaurant <-> Brasserie
    (1824, 2623),  # auto sem-all Basque Restaurant <-> Brasserie
    (1825, 2623),  # auto sem-all Ethiopian Restaurant <-> Brasserie
    (1830, 2623),  # auto sem-all Bulgarian Restaurant <-> Brasserie
    (1842, 2623),  # auto sem-all Cuban Restaurant <-> Brasserie
    (1849, 2623),  # auto sem-all Belgian Restaurant <-> Brasserie
    (1854, 2623),  # auto sem-all Czech Restaurant <-> Brasserie
    (1857, 2623),  # auto sem-all Catalan Restaurant <-> Brasserie
    (1864, 2623),  # auto sem-all Indo Chinese Restaurant <-> Brasserie
    (1883, 2623),  # auto sem-all Egyptian Restaurant <-> Brasserie
    (1890, 2623),  # auto sem-all Colombian Restaurant <-> Brasserie
    (1899, 2623),  # auto sem-all Mongolian Restaurant <-> Brasserie
    (1902, 2623),  # auto sem-all Afghan Restaurant <-> Brasserie
    (1907, 2623),  # auto sem-all Asian Fusion Restaurant <-> Brasserie
    (1908, 2623),  # auto sem-all Austrian Restaurant <-> Brasserie
    (1913, 2623),  # auto sem-all Polynesian Restaurant <-> Brasserie
    (1919, 2623),  # auto sem-all Georgian Restaurant <-> Brasserie
    (1920, 2623),  # auto sem-all Swiss Restaurant <-> Brasserie
    (1922, 2623),  # auto sem-all Chilean Restaurant <-> Brasserie
    (1929, 2623),  # auto sem-all Jamaican Restaurant <-> Brasserie
    (1934, 2623),  # auto sem-all Sri Lankan Restaurant <-> Brasserie
    (1944, 2623),  # auto sem-all Nigerian Restaurant <-> Brasserie
    (1945, 2623),  # auto sem-all Tatar Restaurant <-> Brasserie
    (1946, 2623),  # auto sem-all Slovakian Restaurant <-> Brasserie
    (1948, 2623),  # auto sem-all Bangladeshi Restaurant <-> Brasserie
    (1955, 2623),  # auto sem-all Canadian Restaurant <-> Brasserie
    (1956, 2623),  # auto sem-all Romanian Restaurant <-> Brasserie
    (1957, 2623),  # auto sem-all Honduran Restaurant <-> Brasserie
    (1959, 2623),  # auto sem-all Puerto Rican Restaurant <-> Brasserie
    (1960, 2623),  # auto sem-all Azerbaijani Restaurant <-> Brasserie
    (1962, 2623),  # auto sem-all Molecular Gastronomy Restaurant <-> Brasserie
    (1963, 2623),  # auto sem-all Singaporean Restaurant <-> Brasserie
    (1968, 2623),  # auto sem-all Irish Restaurant <-> Brasserie
    (1970, 2623),  # auto sem-all Venezuelan Restaurant <-> Brasserie
    (1972, 2623),  # auto sem-all Haitian Restaurant <-> Brasserie
    (1973, 2623),  # auto sem-all Uzbek Restaurant <-> Brasserie
    (1975, 2623),  # auto sem-all Dominican Restaurant <-> Brasserie
    (1980, 2623),  # auto sem-all Israeli Restaurant <-> Brasserie
    (1982, 2623),  # auto sem-all Syrian Restaurant <-> Brasserie
    (1987, 2623),  # auto sem-all Ecuadorian Restaurant <-> Brasserie
    (1989, 2623),  # auto sem-all Iberian Restaurant <-> Brasserie
    (1991, 2623),  # auto sem-all Guatemalan Restaurant <-> Brasserie
    (1993, 2623),  # auto sem-all Nicaraguan Restaurant <-> Brasserie
    (1994, 2623),  # auto sem-all Armenian Restaurant <-> Brasserie
    (1998, 2623),  # auto sem-all Senegalese Restaurant <-> Brasserie
    (2000, 2623),  # auto sem-all Costa Rican Restaurant <-> Brasserie
    (2001, 2623),  # auto sem-all Kurdish Restaurant <-> Brasserie
    (2002, 2623),  # auto sem-all Paraguayan Restaurant <-> Brasserie
    (2003, 2623),  # auto sem-all Belarusian Restaurant <-> Brasserie
    (2004, 2623),  # auto sem-all Uruguayan Restaurant <-> Brasserie
    (2005, 2623),  # auto sem-all Scottish Restaurant <-> Brasserie
    (2006, 2623),  # auto sem-all Belizean Restaurant <-> Brasserie
    (2036, 2623),  # auto sem-all International Restaurant <-> Brasserie
    (2053, 2623),  # auto sem-all Bagel Restaurant <-> Brasserie
    (2056, 2623),  # auto sem-all Cheesesteak Restaurant <-> Brasserie
    (2090, 2623),  # auto sem-all Piadina Restaurant <-> Brasserie
    (2098, 2623),  # auto sem-all Wild Game Meats Restaurant <-> Brasserie
    (2100, 2623),  # auto sem-all Oriental Restaurant <-> Brasserie
    (2189, 2623),  # auto sem-all Waffle Restaurant <-> Brasserie
    (2201, 2623),  # auto sem-all Haute Cuisine Restaurant <-> Brasserie
    (2207, 2623),  # auto sem-all Danish Restaurant <-> Brasserie
    (2208, 2623),  # auto sem-all Serbo Croation Restaurant <-> Brasserie
    (2209, 2623),  # auto sem-all Rotisserie Chicken Restaurant <-> Brasserie
    (2287, 2623),  # auto sem-all Kofta Restaurant <-> Brasserie
    (2293, 2623),  # auto sem-all Wok Restaurant <-> Brasserie
    (2295, 2623),  # auto sem-all Potato Restaurant <-> Brasserie
    (2324, 2623),  # auto sem-all Pan Asian Restaurant <-> Brasserie
    (2363, 2623),  # auto sem-all Dumpling Restaurant <-> Brasserie
    (2372, 2623),  # auto sem-all Curry Sausage Restaurant <-> Brasserie
    (2398, 2623),  # auto sem-all Falafel Restaurant <-> Brasserie
    (2421, 2623),  # auto sem-all Laotian Restaurant <-> Brasserie
    (2423, 2623),  # auto sem-all Flatbread Restaurant <-> Brasserie
    (2427, 2623),  # auto sem-all Jewish Restaurant <-> Brasserie
    (2433, 2623),  # auto sem-all Poutinerie Restaurant <-> Brasserie
    (2456, 2623),  # auto sem-all Empanadas <-> Brasserie
    (2552, 2623),  # auto sem-all Diy Foods Restaurant <-> Brasserie
    (2611, 2623),  # auto sem-all Vegan Restaurant <-> Brasserie
    (2623, 2637),  # auto sem-all Brasserie <-> Meat Restaurant
    (2623, 2669),  # auto sem-all Brasserie <-> Oaxacan Restaurant
    (73, 79),  # auto sem-all Car Pooling Station <-> Charging Station
    (75, 79),  # auto sem-all Car Sharing Station <-> Charging Station
    (81, 2043),  # auto sem-all Clinic <-> Urgent Care Clinic
    (126, 182),  # auto sem-all Money Transfer Station <-> Waste Transfer Station
    (216, 1575),  # auto sem-all LGBTQ+ Nightclub <-> Jazz and Blues
    (323, 327),  # auto sem-all Cable Barrier <-> Cycle Barrier
    (327, 339),  # auto sem-all Cycle Barrier <-> Motorcycle Barrier
    (517, 2296),  # auto sem-all Counselling Center <-> Suicide Prevention Services
    (559, 561),  # auto sem-all Service Road <-> Service Area
    (730, 771),  # auto sem-all Water Park <-> Skate Park
    (730, 2188),  # auto sem-all Water Park <-> State Park
    (771, 2188),  # auto sem-all Skate Park <-> State Park
    (1354, 1383),  # auto sem-all Train Route <-> Tram Route
    (1456, 1705),  # auto sem-all High School <-> Flight School
    (1560, 2328),  # auto sem-all Pediatrician <-> Emergency Medicine
    (1575, 2580),  # auto sem-all Jazz and Blues <-> Club Crawl
    (1947, 2237),  # auto sem-all Psychiatrist <-> Child Psychiatrist
    (2655, 2658),  # auto sem-all Home Entrance <-> Shop Entrance
    (1543, 2623),  # auto sem-all Vegetarian Restaurant <-> Brasserie
    (2, 2665),  # auto sem-all Footbridge <-> Bridge
    (4, 1353),  # auto sem-all Administrative Boundary <-> Boundary line
    (56, 1816),  # auto sem-all Animal Boarding Facility <-> Horse Boarding
    (57, 2430),  # auto sem-all Animal Breeding Facility <-> Pig Farm
    (65, 193),  # auto sem-all Bicycle Parking <-> Bicycle Lockers
    (65, 194),  # auto sem-all Bicycle Parking <-> Bicycle Shed
    (66, 2082),  # auto sem-all Bicycle Rental <-> Bike Sharing
    (66, 2370),  # auto sem-all Bicycle Rental <-> Party Bike Rental
    (69, 1428),  # auto sem-all Boat Rental <-> Jet Skis Rental
    (69, 1644),  # auto sem-all Boat Rental <-> Canoe and Kayak Hire Service
    (74, 1608),  # auto sem-all Car Rental <-> Truck Rentals
    (77, 1436),  # auto sem-all Car Wash <-> Auto Detailing
    (82, 271),  # auto sem-all Bread Vending Machine <-> Bicycle Inner Tube Vending Machine
    (82, 272),  # auto sem-all Bread Vending Machine <-> Bottle Return Machine
    (82, 273),  # auto sem-all Bread Vending Machine <-> Parking Ticket Vending Machine
    (82, 274),  # auto sem-all Bread Vending Machine <-> Cigarette Vending Machine
    (82, 275),  # auto sem-all Bread Vending Machine <-> Coffee Vending Machine
    (82, 276),  # auto sem-all Bread Vending Machine <-> Condom Vending Machine
    (82, 279),  # auto sem-all Bread Vending Machine <-> Electronics Vending Machine
    (82, 280),  # auto sem-all Bread Vending Machine <-> Flat Coin Vending Machine
    (82, 282),  # auto sem-all Bread Vending Machine <-> Excrement Bag Dispenser
    (82, 283),  # auto sem-all Bread Vending Machine <-> Feminine Hygiene Vending Machine
    (82, 285),  # auto sem-all Bread Vending Machine <-> Gas Pump
    (82, 288),  # auto sem-all Bread Vending Machine <-> Newspaper Vending Machine
    (82, 290),  # auto sem-all Bread Vending Machine <-> Transit Ticket Vending Machine
    (82, 291),  # auto sem-all Bread Vending Machine <-> Postage Vending Machine
    (82, 2143),  # auto sem-all Bread Vending Machine <-> Rental Kiosks
    (83, 199),  # auto sem-all Clock <-> Sundial
    (86, 1718),  # auto sem-all Convention Center <-> Auditorium
    (102, 2014),  # auto sem-all Gas Station <-> Natural Gas Supplier
    (124, 1452),  # auto sem-all Marketplace <-> Farmers Market
    (124, 2099),  # auto sem-all Marketplace <-> Holiday Market
    (124, 2137),  # auto sem-all Marketplace <-> Seafood Market
    (134, 218),  # auto sem-all Parking Lot <-> Multilevel Parking Garage
    (134, 219),  # auto sem-all Parking Lot <-> Park & Ride Lot
    (134, 220),  # auto sem-all Parking Lot <-> Street-side Parking
    (134, 2405),  # auto sem-all Parking Lot <-> Valet Service
    (136, 223),  # auto sem-all Parking Space <-> Accessible Parking Space
    (148, 1702),  # auto sem-all Public Bath <-> Onsen
    (151, 191),  # auto sem-all Recycling Center <-> Recycling
    (151, 299),  # auto sem-all Recycling Center <-> Green Waste Container
    (152, 191),  # auto sem-all Recycling Container <-> Recycling
    (152, 298),  # auto sem-all Recycling Container <-> E-Waste Container
    (152, 299),  # auto sem-all Recycling Container <-> Green Waste Container
    (159, 256),  # auto sem-all Shelter <-> Gazebo
    (159, 257),  # auto sem-all Shelter <-> Lean-To
    (159, 258),  # auto sem-all Shelter <-> Picnic Shelter
    (159, 259),  # auto sem-all Shelter <-> Transit Shelter
    (165, 265),  # auto sem-all Studio <-> Recording Studio
    (165, 266),  # auto sem-all Studio <-> Radio Station
    (165, 267),  # auto sem-all Studio <-> Television Station
    (165, 268),  # auto sem-all Studio <-> Film Studio
    (165, 1988),  # auto sem-all Studio <-> Animation Studio
    (165, 2120),  # auto sem-all Studio <-> Recording and Rehearsal Studio
    (165, 2436),  # auto sem-all Studio <-> Art Space Rental
    (166, 2150),  # auto sem-all Taxi Stand <-> Town Car Service
    (166, 2575),  # auto sem-all Taxi Stand <-> Pedicab Service
    (172, 301),  # auto sem-all Restroom <-> Flush Toilets
    (172, 1927),  # auto sem-all Restroom <-> Public Toilet
    (175, 193),  # auto sem-all Bicycle Parking Garage <-> Bicycle Lockers
    (175, 194),  # auto sem-all Bicycle Parking Garage <-> Bicycle Shed
    (178, 271),  # auto sem-all Vending Machine <-> Bicycle Inner Tube Vending Machine
    (178, 272),  # auto sem-all Vending Machine <-> Bottle Return Machine
    (178, 273),  # auto sem-all Vending Machine <-> Parking Ticket Vending Machine
    (178, 274),  # auto sem-all Vending Machine <-> Cigarette Vending Machine
    (178, 279),  # auto sem-all Vending Machine <-> Electronics Vending Machine
    (178, 280),  # auto sem-all Vending Machine <-> Flat Coin Vending Machine
    (178, 282),  # auto sem-all Vending Machine <-> Excrement Bag Dispenser
    (178, 283),  # auto sem-all Vending Machine <-> Feminine Hygiene Vending Machine
    (178, 285),  # auto sem-all Vending Machine <-> Gas Pump
    (178, 286),  # auto sem-all Vending Machine <-> Ice Cream Vending Machine
    (178, 288),  # auto sem-all Vending Machine <-> Newspaper Vending Machine
    (178, 290),  # auto sem-all Vending Machine <-> Transit Ticket Vending Machine
    (178, 291),  # auto sem-all Vending Machine <-> Postage Vending Machine
    (178, 2143),  # auto sem-all Vending Machine <-> Rental Kiosks
    (180, 293),  # auto sem-all Waste Basket <-> Dog Excrement Bin
    (193, 194),  # auto sem-all Bicycle Lockers <-> Bicycle Shed
    (218, 221),  # auto sem-all Multilevel Parking Garage <-> Underground Parking
    (220, 221),  # auto sem-all Street-side Parking <-> Underground Parking
    (220, 2405),  # auto sem-all Street-side Parking <-> Valet Service
    (221, 2405),  # auto sem-all Underground Parking <-> Valet Service
    (256, 257),  # auto sem-all Gazebo <-> Lean-To
    (256, 258),  # auto sem-all Gazebo <-> Picnic Shelter
    (256, 259),  # auto sem-all Gazebo <-> Transit Shelter
    (257, 258),  # auto sem-all Lean-To <-> Picnic Shelter
    (257, 259),  # auto sem-all Lean-To <-> Transit Shelter
    (258, 259),  # auto sem-all Picnic Shelter <-> Transit Shelter
    (265, 266),  # auto sem-all Recording Studio <-> Radio Station
    (265, 267),  # auto sem-all Recording Studio <-> Television Station
    (265, 268),  # auto sem-all Recording Studio <-> Film Studio
    (265, 1988),  # auto sem-all Recording Studio <-> Animation Studio
    (265, 2120),  # auto sem-all Recording Studio <-> Recording and Rehearsal Studio
    (265, 2436),  # auto sem-all Recording Studio <-> Art Space Rental
    (266, 268),  # auto sem-all Radio Station <-> Film Studio
    (266, 1988),  # auto sem-all Radio Station <-> Animation Studio
    (266, 2436),  # auto sem-all Radio Station <-> Art Space Rental
    (267, 268),  # auto sem-all Television Station <-> Film Studio
    (267, 1988),  # auto sem-all Television Station <-> Animation Studio
    (267, 2436),  # auto sem-all Television Station <-> Art Space Rental
    (268, 1988),  # auto sem-all Film Studio <-> Animation Studio
    (268, 2436),  # auto sem-all Film Studio <-> Art Space Rental
    (269, 301),  # auto sem-all Portable Toilet <-> Flush Toilets
    (269, 1927),  # auto sem-all Portable Toilet <-> Public Toilet
    (271, 272),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Bottle Return Machine
    (271, 273),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Parking Ticket Vending Machine
    (271, 274),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Cigarette Vending Machine
    (271, 275),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Coffee Vending Machine
    (271, 276),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Condom Vending Machine
    (271, 277),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Drink Vending Machine
    (271, 278),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Egg Vending Machine
    (271, 279),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Electronics Vending Machine
    (271, 280),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Flat Coin Vending Machine
    (271, 282),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Excrement Bag Dispenser
    (271, 283),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Feminine Hygiene Vending Machine
    (271, 284),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Food Vending Machine
    (271, 285),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Gas Pump
    (271, 286),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Ice Cream Vending Machine
    (271, 287),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Ice Vending Machine
    (271, 288),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Newspaper Vending Machine
    (271, 289),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Pizza Vending Machine
    (271, 291),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Postage Vending Machine
    (271, 292),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Snack Vending Machine
    (271, 2143),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Rental Kiosks
    (272, 273),  # auto sem-all Bottle Return Machine <-> Parking Ticket Vending Machine
    (272, 274),  # auto sem-all Bottle Return Machine <-> Cigarette Vending Machine
    (272, 275),  # auto sem-all Bottle Return Machine <-> Coffee Vending Machine
    (272, 276),  # auto sem-all Bottle Return Machine <-> Condom Vending Machine
    (272, 277),  # auto sem-all Bottle Return Machine <-> Drink Vending Machine
    (272, 278),  # auto sem-all Bottle Return Machine <-> Egg Vending Machine
    (272, 279),  # auto sem-all Bottle Return Machine <-> Electronics Vending Machine
    (272, 280),  # auto sem-all Bottle Return Machine <-> Flat Coin Vending Machine
    (272, 282),  # auto sem-all Bottle Return Machine <-> Excrement Bag Dispenser
    (272, 283),  # auto sem-all Bottle Return Machine <-> Feminine Hygiene Vending Machine
    (272, 284),  # auto sem-all Bottle Return Machine <-> Food Vending Machine
    (272, 285),  # auto sem-all Bottle Return Machine <-> Gas Pump
    (272, 286),  # auto sem-all Bottle Return Machine <-> Ice Cream Vending Machine
    (272, 287),  # auto sem-all Bottle Return Machine <-> Ice Vending Machine
    (272, 288),  # auto sem-all Bottle Return Machine <-> Newspaper Vending Machine
    (272, 289),  # auto sem-all Bottle Return Machine <-> Pizza Vending Machine
    (272, 290),  # auto sem-all Bottle Return Machine <-> Transit Ticket Vending Machine
    (272, 291),  # auto sem-all Bottle Return Machine <-> Postage Vending Machine
    (272, 292),  # auto sem-all Bottle Return Machine <-> Snack Vending Machine
    (272, 2143),  # auto sem-all Bottle Return Machine <-> Rental Kiosks
    (273, 274),  # auto sem-all Parking Ticket Vending Machine <-> Cigarette Vending Machine
    (273, 275),  # auto sem-all Parking Ticket Vending Machine <-> Coffee Vending Machine
    (273, 276),  # auto sem-all Parking Ticket Vending Machine <-> Condom Vending Machine
    (273, 277),  # auto sem-all Parking Ticket Vending Machine <-> Drink Vending Machine
    (273, 278),  # auto sem-all Parking Ticket Vending Machine <-> Egg Vending Machine
    (273, 279),  # auto sem-all Parking Ticket Vending Machine <-> Electronics Vending Machine
    (273, 280),  # auto sem-all Parking Ticket Vending Machine <-> Flat Coin Vending Machine
    (273, 282),  # auto sem-all Parking Ticket Vending Machine <-> Excrement Bag Dispenser
    (273, 283),  # auto sem-all Parking Ticket Vending Machine <-> Feminine Hygiene Vending Machine
    (273, 284),  # auto sem-all Parking Ticket Vending Machine <-> Food Vending Machine
    (273, 285),  # auto sem-all Parking Ticket Vending Machine <-> Gas Pump
    (273, 286),  # auto sem-all Parking Ticket Vending Machine <-> Ice Cream Vending Machine
    (273, 287),  # auto sem-all Parking Ticket Vending Machine <-> Ice Vending Machine
    (273, 288),  # auto sem-all Parking Ticket Vending Machine <-> Newspaper Vending Machine
    (273, 289),  # auto sem-all Parking Ticket Vending Machine <-> Pizza Vending Machine
    (273, 291),  # auto sem-all Parking Ticket Vending Machine <-> Postage Vending Machine
    (273, 292),  # auto sem-all Parking Ticket Vending Machine <-> Snack Vending Machine
    (273, 2143),  # auto sem-all Parking Ticket Vending Machine <-> Rental Kiosks
    (274, 276),  # auto sem-all Cigarette Vending Machine <-> Condom Vending Machine
    (274, 277),  # auto sem-all Cigarette Vending Machine <-> Drink Vending Machine
    (274, 278),  # auto sem-all Cigarette Vending Machine <-> Egg Vending Machine
    (274, 279),  # auto sem-all Cigarette Vending Machine <-> Electronics Vending Machine
    (274, 280),  # auto sem-all Cigarette Vending Machine <-> Flat Coin Vending Machine
    (274, 282),  # auto sem-all Cigarette Vending Machine <-> Excrement Bag Dispenser
    (274, 283),  # auto sem-all Cigarette Vending Machine <-> Feminine Hygiene Vending Machine
    (274, 284),  # auto sem-all Cigarette Vending Machine <-> Food Vending Machine
    (274, 285),  # auto sem-all Cigarette Vending Machine <-> Gas Pump
    (274, 286),  # auto sem-all Cigarette Vending Machine <-> Ice Cream Vending Machine
    (274, 288),  # auto sem-all Cigarette Vending Machine <-> Newspaper Vending Machine
    (274, 289),  # auto sem-all Cigarette Vending Machine <-> Pizza Vending Machine
    (274, 290),  # auto sem-all Cigarette Vending Machine <-> Transit Ticket Vending Machine
    (274, 291),  # auto sem-all Cigarette Vending Machine <-> Postage Vending Machine
    (274, 292),  # auto sem-all Cigarette Vending Machine <-> Snack Vending Machine
    (274, 2143),  # auto sem-all Cigarette Vending Machine <-> Rental Kiosks
    (275, 277),  # auto sem-all Coffee Vending Machine <-> Drink Vending Machine
    (275, 279),  # auto sem-all Coffee Vending Machine <-> Electronics Vending Machine
    (275, 280),  # auto sem-all Coffee Vending Machine <-> Flat Coin Vending Machine
    (275, 282),  # auto sem-all Coffee Vending Machine <-> Excrement Bag Dispenser
    (275, 283),  # auto sem-all Coffee Vending Machine <-> Feminine Hygiene Vending Machine
    (275, 285),  # auto sem-all Coffee Vending Machine <-> Gas Pump
    (275, 288),  # auto sem-all Coffee Vending Machine <-> Newspaper Vending Machine
    (275, 289),  # auto sem-all Coffee Vending Machine <-> Pizza Vending Machine
    (275, 290),  # auto sem-all Coffee Vending Machine <-> Transit Ticket Vending Machine
    (275, 292),  # auto sem-all Coffee Vending Machine <-> Snack Vending Machine
    (275, 2143),  # auto sem-all Coffee Vending Machine <-> Rental Kiosks
    (276, 277),  # auto sem-all Condom Vending Machine <-> Drink Vending Machine
    (276, 278),  # auto sem-all Condom Vending Machine <-> Egg Vending Machine
    (276, 279),  # auto sem-all Condom Vending Machine <-> Electronics Vending Machine
    (276, 282),  # auto sem-all Condom Vending Machine <-> Excrement Bag Dispenser
    (276, 283),  # auto sem-all Condom Vending Machine <-> Feminine Hygiene Vending Machine
    (276, 285),  # auto sem-all Condom Vending Machine <-> Gas Pump
    (276, 286),  # auto sem-all Condom Vending Machine <-> Ice Cream Vending Machine
    (276, 288),  # auto sem-all Condom Vending Machine <-> Newspaper Vending Machine
    (276, 289),  # auto sem-all Condom Vending Machine <-> Pizza Vending Machine
    (276, 290),  # auto sem-all Condom Vending Machine <-> Transit Ticket Vending Machine
    (276, 291),  # auto sem-all Condom Vending Machine <-> Postage Vending Machine
    (276, 292),  # auto sem-all Condom Vending Machine <-> Snack Vending Machine
    (276, 2143),  # auto sem-all Condom Vending Machine <-> Rental Kiosks
    (277, 279),  # auto sem-all Drink Vending Machine <-> Electronics Vending Machine
    (277, 280),  # auto sem-all Drink Vending Machine <-> Flat Coin Vending Machine
    (277, 282),  # auto sem-all Drink Vending Machine <-> Excrement Bag Dispenser
    (277, 283),  # auto sem-all Drink Vending Machine <-> Feminine Hygiene Vending Machine
    (277, 285),  # auto sem-all Drink Vending Machine <-> Gas Pump
    (277, 286),  # auto sem-all Drink Vending Machine <-> Ice Cream Vending Machine
    (277, 288),  # auto sem-all Drink Vending Machine <-> Newspaper Vending Machine
    (277, 290),  # auto sem-all Drink Vending Machine <-> Transit Ticket Vending Machine
    (277, 291),  # auto sem-all Drink Vending Machine <-> Postage Vending Machine
    (277, 2143),  # auto sem-all Drink Vending Machine <-> Rental Kiosks
    (278, 279),  # auto sem-all Egg Vending Machine <-> Electronics Vending Machine
    (278, 280),  # auto sem-all Egg Vending Machine <-> Flat Coin Vending Machine
    (278, 282),  # auto sem-all Egg Vending Machine <-> Excrement Bag Dispenser
    (278, 283),  # auto sem-all Egg Vending Machine <-> Feminine Hygiene Vending Machine
    (278, 285),  # auto sem-all Egg Vending Machine <-> Gas Pump
    (278, 286),  # auto sem-all Egg Vending Machine <-> Ice Cream Vending Machine
    (278, 288),  # auto sem-all Egg Vending Machine <-> Newspaper Vending Machine
    (278, 290),  # auto sem-all Egg Vending Machine <-> Transit Ticket Vending Machine
    (278, 2143),  # auto sem-all Egg Vending Machine <-> Rental Kiosks
    (279, 280),  # auto sem-all Electronics Vending Machine <-> Flat Coin Vending Machine
    (279, 282),  # auto sem-all Electronics Vending Machine <-> Excrement Bag Dispenser
    (279, 283),  # auto sem-all Electronics Vending Machine <-> Feminine Hygiene Vending Machine
    (279, 284),  # auto sem-all Electronics Vending Machine <-> Food Vending Machine
    (279, 285),  # auto sem-all Electronics Vending Machine <-> Gas Pump
    (279, 286),  # auto sem-all Electronics Vending Machine <-> Ice Cream Vending Machine
    (279, 287),  # auto sem-all Electronics Vending Machine <-> Ice Vending Machine
    (279, 288),  # auto sem-all Electronics Vending Machine <-> Newspaper Vending Machine
    (279, 289),  # auto sem-all Electronics Vending Machine <-> Pizza Vending Machine
    (279, 290),  # auto sem-all Electronics Vending Machine <-> Transit Ticket Vending Machine
    (279, 291),  # auto sem-all Electronics Vending Machine <-> Postage Vending Machine
    (279, 292),  # auto sem-all Electronics Vending Machine <-> Snack Vending Machine
    (279, 2143),  # auto sem-all Electronics Vending Machine <-> Rental Kiosks
    (280, 282),  # auto sem-all Flat Coin Vending Machine <-> Excrement Bag Dispenser
    (280, 283),  # auto sem-all Flat Coin Vending Machine <-> Feminine Hygiene Vending Machine
    (280, 285),  # auto sem-all Flat Coin Vending Machine <-> Gas Pump
    (280, 286),  # auto sem-all Flat Coin Vending Machine <-> Ice Cream Vending Machine
    (280, 287),  # auto sem-all Flat Coin Vending Machine <-> Ice Vending Machine
    (280, 288),  # auto sem-all Flat Coin Vending Machine <-> Newspaper Vending Machine
    (280, 289),  # auto sem-all Flat Coin Vending Machine <-> Pizza Vending Machine
    (280, 291),  # auto sem-all Flat Coin Vending Machine <-> Postage Vending Machine
    (280, 292),  # auto sem-all Flat Coin Vending Machine <-> Snack Vending Machine
    (280, 2143),  # auto sem-all Flat Coin Vending Machine <-> Rental Kiosks
    (282, 283),  # auto sem-all Excrement Bag Dispenser <-> Feminine Hygiene Vending Machine
    (282, 284),  # auto sem-all Excrement Bag Dispenser <-> Food Vending Machine
    (282, 285),  # auto sem-all Excrement Bag Dispenser <-> Gas Pump
    (282, 286),  # auto sem-all Excrement Bag Dispenser <-> Ice Cream Vending Machine
    (282, 287),  # auto sem-all Excrement Bag Dispenser <-> Ice Vending Machine
    (282, 288),  # auto sem-all Excrement Bag Dispenser <-> Newspaper Vending Machine
    (282, 289),  # auto sem-all Excrement Bag Dispenser <-> Pizza Vending Machine
    (282, 291),  # auto sem-all Excrement Bag Dispenser <-> Postage Vending Machine
    (282, 292),  # auto sem-all Excrement Bag Dispenser <-> Snack Vending Machine
    (282, 2143),  # auto sem-all Excrement Bag Dispenser <-> Rental Kiosks
    (283, 284),  # auto sem-all Feminine Hygiene Vending Machine <-> Food Vending Machine
    (283, 285),  # auto sem-all Feminine Hygiene Vending Machine <-> Gas Pump
    (283, 286),  # auto sem-all Feminine Hygiene Vending Machine <-> Ice Cream Vending Machine
    (283, 287),  # auto sem-all Feminine Hygiene Vending Machine <-> Ice Vending Machine
    (283, 288),  # auto sem-all Feminine Hygiene Vending Machine <-> Newspaper Vending Machine
    (283, 289),  # auto sem-all Feminine Hygiene Vending Machine <-> Pizza Vending Machine
    (283, 290),  # auto sem-all Feminine Hygiene Vending Machine <-> Transit Ticket Vending Machine
    (283, 291),  # auto sem-all Feminine Hygiene Vending Machine <-> Postage Vending Machine
    (283, 292),  # auto sem-all Feminine Hygiene Vending Machine <-> Snack Vending Machine
    (283, 2143),  # auto sem-all Feminine Hygiene Vending Machine <-> Rental Kiosks
    (284, 285),  # auto sem-all Food Vending Machine <-> Gas Pump
    (284, 286),  # auto sem-all Food Vending Machine <-> Ice Cream Vending Machine
    (284, 288),  # auto sem-all Food Vending Machine <-> Newspaper Vending Machine
    (284, 289),  # auto sem-all Food Vending Machine <-> Pizza Vending Machine
    (284, 290),  # auto sem-all Food Vending Machine <-> Transit Ticket Vending Machine
    (284, 291),  # auto sem-all Food Vending Machine <-> Postage Vending Machine
    (284, 292),  # auto sem-all Food Vending Machine <-> Snack Vending Machine
    (284, 2143),  # auto sem-all Food Vending Machine <-> Rental Kiosks
    (285, 286),  # auto sem-all Gas Pump <-> Ice Cream Vending Machine
    (285, 287),  # auto sem-all Gas Pump <-> Ice Vending Machine
    (285, 288),  # auto sem-all Gas Pump <-> Newspaper Vending Machine
    (285, 289),  # auto sem-all Gas Pump <-> Pizza Vending Machine
    (285, 291),  # auto sem-all Gas Pump <-> Postage Vending Machine
    (285, 292),  # auto sem-all Gas Pump <-> Snack Vending Machine
    (285, 2143),  # auto sem-all Gas Pump <-> Rental Kiosks
    (286, 288),  # auto sem-all Ice Cream Vending Machine <-> Newspaper Vending Machine
    (286, 289),  # auto sem-all Ice Cream Vending Machine <-> Pizza Vending Machine
    (286, 290),  # auto sem-all Ice Cream Vending Machine <-> Transit Ticket Vending Machine
    (286, 291),  # auto sem-all Ice Cream Vending Machine <-> Postage Vending Machine
    (286, 292),  # auto sem-all Ice Cream Vending Machine <-> Snack Vending Machine
    (286, 2143),  # auto sem-all Ice Cream Vending Machine <-> Rental Kiosks
    (287, 288),  # auto sem-all Ice Vending Machine <-> Newspaper Vending Machine
    (287, 290),  # auto sem-all Ice Vending Machine <-> Transit Ticket Vending Machine
    (287, 2143),  # auto sem-all Ice Vending Machine <-> Rental Kiosks
    (288, 289),  # auto sem-all Newspaper Vending Machine <-> Pizza Vending Machine
    (288, 290),  # auto sem-all Newspaper Vending Machine <-> Transit Ticket Vending Machine
    (288, 291),  # auto sem-all Newspaper Vending Machine <-> Postage Vending Machine
    (288, 292),  # auto sem-all Newspaper Vending Machine <-> Snack Vending Machine
    (288, 2143),  # auto sem-all Newspaper Vending Machine <-> Rental Kiosks
    (289, 290),  # auto sem-all Pizza Vending Machine <-> Transit Ticket Vending Machine
    (289, 2143),  # auto sem-all Pizza Vending Machine <-> Rental Kiosks
    (290, 291),  # auto sem-all Transit Ticket Vending Machine <-> Postage Vending Machine
    (290, 292),  # auto sem-all Transit Ticket Vending Machine <-> Snack Vending Machine
    (291, 2143),  # auto sem-all Postage Vending Machine <-> Rental Kiosks
    (292, 2143),  # auto sem-all Snack Vending Machine <-> Rental Kiosks
    (301, 302),  # auto sem-all Flush Toilets <-> Pit Latrine
    (305, 321),  # auto sem-all Bollard Row <-> Bollard
    (313, 2691),  # auto sem-all Gate <-> Emergency Gate
    (328, 351),  # auto sem-all Trench <-> Barrier Ditch
    (329, 357),  # auto sem-all Fence <-> Railing
    (349, 362),  # auto sem-all Wall <-> Noise Barrier
    (447, 1449),  # auto sem-all Photographer <-> Event Photography
    (447, 2332),  # auto sem-all Photographer <-> Real Estate Photography
    (492, 493),  # auto sem-all Emergency Water Reservoir <-> Emergency Water Reservoir (Underground)
    (494, 678),  # auto sem-all Emergency Water Tank <-> Reservoir Landuse
    (531, 604),  # auto sem-all Path <-> Informal Path
    (544, 599),  # auto sem-all Foot Path <-> Informal Foot Path
    (555, 605),  # auto sem-all Motorsport Racetrack <-> Karting Racetrack
    (559, 608),  # auto sem-all Service Road <-> Alley
    (559, 610),  # auto sem-all Service Road <-> Drive-Through
    (559, 611),  # auto sem-all Service Road <-> Driveway
    (559, 612),  # auto sem-all Service Road <-> Emergency Access
    (559, 613),  # auto sem-all Service Road <-> Parking Aisle
    (569, 638),  # auto sem-all Room <-> Indoor Stairwell
    (580, 593),  # auto sem-all Crosswalk (marked) <-> Crosswalk (other)
    (580, 617),  # auto sem-all Crosswalk (marked) <-> Marked Cycle Crossing
    (581, 595),  # auto sem-all Crosswalk with Signals <-> Crossing With Pedestrian Signals
    (582, 618),  # auto sem-all Unmarked Crosswalk <-> Unmarked Cycle Crossing
    (583, 695),  # auto sem-all Dance Hall <-> Dance School
    (583, 2086),  # auto sem-all Dance Hall <-> Country Dance Hall
    (585, 601),  # auto sem-all Crosswalk (footway) <-> Crosswalk (zebra)
    (591, 614),  # auto sem-all Moving Walkway <-> Escalator
    (593, 617),  # auto sem-all Crosswalk (other) <-> Marked Cycle Crossing
    (595, 2660),  # auto sem-all Crossing With Pedestrian Signals <-> Crosswalk with Signals
    (608, 610),  # auto sem-all Alley <-> Drive-Through
    (608, 611),  # auto sem-all Alley <-> Driveway
    (608, 612),  # auto sem-all Alley <-> Emergency Access
    (608, 613),  # auto sem-all Alley <-> Parking Aisle
    (610, 611),  # auto sem-all Drive-Through <-> Driveway
    (610, 612),  # auto sem-all Drive-Through <-> Emergency Access
    (610, 613),  # auto sem-all Drive-Through <-> Parking Aisle
    (611, 612),  # auto sem-all Driveway <-> Emergency Access
    (611, 613),  # auto sem-all Driveway <-> Parking Aisle
    (612, 613),  # auto sem-all Emergency Access <-> Parking Aisle
    (657, 1807),  # auto sem-all Industrial Area <-> Mining
    (657, 2198),  # auto sem-all Industrial Area <-> Rice Mill
    (657, 2229),  # auto sem-all Industrial Area <-> Scrap Metals
    (657, 2540),  # auto sem-all Industrial Area <-> Mills
    (662, 2215),  # auto sem-all Plant Nursery <-> Christmas Trees
    (667, 1769),  # auto sem-all Residential Area <-> Mobile Home Park
    (683, 688),  # auto sem-all Military Base <-> Naval Base
    (713, 745),  # auto sem-all Picnic Table <-> Chess Table
    (715, 779),  # auto sem-all Playground <-> Indoor Playground
    (719, 720),  # auto sem-all Slipway <-> Slipway (Drivable)
    (728, 785),  # auto sem-all Racetrack (Non-Motorsport) <-> Horse Racetrack
    (763, 1531),  # auto sem-all Factory <-> Plastic Manufacturer
    (763, 1602),  # auto sem-all Factory <-> Chemical Plant
    (763, 1603),  # auto sem-all Factory <-> Motorcycle Manufacturer
    (763, 1693),  # auto sem-all Factory <-> Glass Manufacturer
    (763, 2007),  # auto sem-all Factory <-> Aircraft Manufacturer
    (763, 2089),  # auto sem-all Factory <-> Leather Products Manufacturer
    (763, 2319),  # auto sem-all Factory <-> Shoe Factory
    (763, 2506),  # auto sem-all Factory <-> Jewelry Manufacturer
    (763, 2626),  # auto sem-all Factory <-> Cosmetic Products Manufacturer
    (811, 845),  # auto sem-all Mast <-> Communication Mast
    (811, 846),  # auto sem-all Mast <-> Lighting Mast
    (825, 851),  # auto sem-all Surveillance <-> Surveillance Camera
    (826, 859),  # auto sem-all Fen <-> Mangrove
    (826, 876),  # auto sem-all Fen <-> Marsh
    (826, 902),  # auto sem-all Fen <-> Wetland
    (826, 913),  # auto sem-all Fen <-> Bog
    (826, 914),  # auto sem-all Fen <-> Reed bed
    (826, 917),  # auto sem-all Fen <-> Coastal Salt Marsh
    (826, 918),  # auto sem-all Fen <-> String Bog
    (826, 919),  # auto sem-all Fen <-> Swamp
    (826, 920),  # auto sem-all Fen <-> Tidal Flat
    (826, 922),  # auto sem-all Fen <-> Wet Meadow
    (828, 852),  # auto sem-all Tower <-> Bell Tower
    (828, 853),  # auto sem-all Tower <-> Communication Tower
    (828, 854),  # auto sem-all Tower <-> Cooling Tower
    (828, 855),  # auto sem-all Tower <-> Fortified Tower
    (828, 856),  # auto sem-all Tower <-> Minaret
    (828, 857),  # auto sem-all Tower <-> Observation Tower
    (828, 858),  # auto sem-all Tower <-> Pagoda
    (845, 846),  # auto sem-all Communication Mast <-> Lighting Mast
    (848, 1023),  # auto sem-all Underground Pipeline <-> Underground Power Cable
    (852, 853),  # auto sem-all Bell Tower <-> Communication Tower
    (852, 854),  # auto sem-all Bell Tower <-> Cooling Tower
    (852, 855),  # auto sem-all Bell Tower <-> Fortified Tower
    (852, 856),  # auto sem-all Bell Tower <-> Minaret
    (852, 857),  # auto sem-all Bell Tower <-> Observation Tower
    (852, 858),  # auto sem-all Bell Tower <-> Pagoda
    (853, 854),  # auto sem-all Communication Tower <-> Cooling Tower
    (853, 855),  # auto sem-all Communication Tower <-> Fortified Tower
    (853, 856),  # auto sem-all Communication Tower <-> Minaret
    (853, 857),  # auto sem-all Communication Tower <-> Observation Tower
    (853, 858),  # auto sem-all Communication Tower <-> Pagoda
    (854, 855),  # auto sem-all Cooling Tower <-> Fortified Tower
    (854, 856),  # auto sem-all Cooling Tower <-> Minaret
    (854, 857),  # auto sem-all Cooling Tower <-> Observation Tower
    (854, 858),  # auto sem-all Cooling Tower <-> Pagoda
    (855, 856),  # auto sem-all Fortified Tower <-> Minaret
    (855, 857),  # auto sem-all Fortified Tower <-> Observation Tower
    (855, 858),  # auto sem-all Fortified Tower <-> Pagoda
    (856, 857),  # auto sem-all Minaret <-> Observation Tower
    (856, 858),  # auto sem-all Minaret <-> Pagoda
    (857, 858),  # auto sem-all Observation Tower <-> Pagoda
    (859, 876),  # auto sem-all Mangrove <-> Marsh
    (859, 902),  # auto sem-all Mangrove <-> Wetland
    (859, 913),  # auto sem-all Mangrove <-> Bog
    (859, 914),  # auto sem-all Mangrove <-> Reed bed
    (859, 917),  # auto sem-all Mangrove <-> Coastal Salt Marsh
    (859, 918),  # auto sem-all Mangrove <-> String Bog
    (859, 919),  # auto sem-all Mangrove <-> Swamp
    (859, 920),  # auto sem-all Mangrove <-> Tidal Flat
    (859, 922),  # auto sem-all Mangrove <-> Wet Meadow
    (863, 864),  # auto sem-all Utility Marker <-> Power Marker
    (876, 902),  # auto sem-all Marsh <-> Wetland
    (876, 913),  # auto sem-all Marsh <-> Bog
    (876, 914),  # auto sem-all Marsh <-> Reed bed
    (876, 917),  # auto sem-all Marsh <-> Coastal Salt Marsh
    (876, 918),  # auto sem-all Marsh <-> String Bog
    (876, 919),  # auto sem-all Marsh <-> Swamp
    (876, 920),  # auto sem-all Marsh <-> Tidal Flat
    (876, 922),  # auto sem-all Marsh <-> Wet Meadow
    (901, 904),  # auto sem-all Water <-> Basin
    (901, 905),  # auto sem-all Water <-> Canal Area
    (901, 906),  # auto sem-all Water <-> Lake
    (901, 907),  # auto sem-all Water <-> Moat
    (901, 908),  # auto sem-all Water <-> Pond
    (901, 909),  # auto sem-all Water <-> Reservoir
    (901, 910),  # auto sem-all Water <-> River Area
    (901, 911),  # auto sem-all Water <-> Stream Area
    (901, 912),  # auto sem-all Water <-> Wastewater Basin
    (902, 913),  # auto sem-all Wetland <-> Bog
    (902, 914),  # auto sem-all Wetland <-> Reed bed
    (902, 917),  # auto sem-all Wetland <-> Coastal Salt Marsh
    (902, 918),  # auto sem-all Wetland <-> String Bog
    (902, 919),  # auto sem-all Wetland <-> Swamp
    (902, 920),  # auto sem-all Wetland <-> Tidal Flat
    (902, 922),  # auto sem-all Wetland <-> Wet Meadow
    (904, 905),  # auto sem-all Basin <-> Canal Area
    (904, 906),  # auto sem-all Basin <-> Lake
    (904, 907),  # auto sem-all Basin <-> Moat
    (904, 908),  # auto sem-all Basin <-> Pond
    (904, 909),  # auto sem-all Basin <-> Reservoir
    (904, 910),  # auto sem-all Basin <-> River Area
    (904, 911),  # auto sem-all Basin <-> Stream Area
    (904, 912),  # auto sem-all Basin <-> Wastewater Basin
    (905, 906),  # auto sem-all Canal Area <-> Lake
    (905, 907),  # auto sem-all Canal Area <-> Moat
    (905, 908),  # auto sem-all Canal Area <-> Pond
    (905, 909),  # auto sem-all Canal Area <-> Reservoir
    (905, 910),  # auto sem-all Canal Area <-> River Area
    (905, 911),  # auto sem-all Canal Area <-> Stream Area
    (905, 912),  # auto sem-all Canal Area <-> Wastewater Basin
    (906, 907),  # auto sem-all Lake <-> Moat
    (906, 908),  # auto sem-all Lake <-> Pond
    (906, 909),  # auto sem-all Lake <-> Reservoir
    (906, 910),  # auto sem-all Lake <-> River Area
    (906, 911),  # auto sem-all Lake <-> Stream Area
    (906, 912),  # auto sem-all Lake <-> Wastewater Basin
    (907, 908),  # auto sem-all Moat <-> Pond
    (907, 909),  # auto sem-all Moat <-> Reservoir
    (907, 910),  # auto sem-all Moat <-> River Area
    (907, 911),  # auto sem-all Moat <-> Stream Area
    (907, 912),  # auto sem-all Moat <-> Wastewater Basin
    (908, 909),  # auto sem-all Pond <-> Reservoir
    (908, 910),  # auto sem-all Pond <-> River Area
    (908, 911),  # auto sem-all Pond <-> Stream Area
    (908, 912),  # auto sem-all Pond <-> Wastewater Basin
    (909, 910),  # auto sem-all Reservoir <-> River Area
    (909, 911),  # auto sem-all Reservoir <-> Stream Area
    (909, 912),  # auto sem-all Reservoir <-> Wastewater Basin
    (910, 911),  # auto sem-all River Area <-> Stream Area
    (910, 912),  # auto sem-all River Area <-> Wastewater Basin
    (911, 912),  # auto sem-all Stream Area <-> Wastewater Basin
    (913, 914),  # auto sem-all Bog <-> Reed bed
    (913, 917),  # auto sem-all Bog <-> Coastal Salt Marsh
    (913, 918),  # auto sem-all Bog <-> String Bog
    (913, 919),  # auto sem-all Bog <-> Swamp
    (913, 920),  # auto sem-all Bog <-> Tidal Flat
    (913, 922),  # auto sem-all Bog <-> Wet Meadow
    (914, 918),  # auto sem-all Reed bed <-> String Bog
    (914, 919),  # auto sem-all Reed bed <-> Swamp
    (914, 922),  # auto sem-all Reed bed <-> Wet Meadow
    (917, 919),  # auto sem-all Coastal Salt Marsh <-> Swamp
    (918, 919),  # auto sem-all String Bog <-> Swamp
    (918, 920),  # auto sem-all String Bog <-> Tidal Flat
    (918, 922),  # auto sem-all String Bog <-> Wet Meadow
    (919, 920),  # auto sem-all Swamp <-> Tidal Flat
    (919, 922),  # auto sem-all Swamp <-> Wet Meadow
    (920, 922),  # auto sem-all Tidal Flat <-> Wet Meadow
    (1024, 1037),  # auto sem-all Solar Panel <-> Rooftop Solar Panel
    (1024, 1553),  # auto sem-all Solar Panel <-> Solar Installation
    (1037, 1553),  # auto sem-all Rooftop Solar Panel <-> Solar Installation
    (1114, 1371),  # auto sem-all Ferry Route <-> Route (Ferry)
    (1180, 1291),  # auto sem-all Artwork <-> Mural
    (1180, 1316),  # auto sem-all Artwork <-> Bust
    (1180, 1317),  # auto sem-all Artwork <-> Graffiti
    (1180, 1318),  # auto sem-all Artwork <-> Art Installation
    (1180, 1319),  # auto sem-all Artwork <-> Sculpture
    (1180, 2352),  # auto sem-all Artwork <-> Street Art
    (1291, 1316),  # auto sem-all Mural <-> Bust
    (1291, 1317),  # auto sem-all Mural <-> Graffiti
    (1291, 1318),  # auto sem-all Mural <-> Art Installation
    (1291, 1319),  # auto sem-all Mural <-> Sculpture
    (1291, 1320),  # auto sem-all Mural <-> Statue
    (1291, 2352),  # auto sem-all Mural <-> Street Art
    (1300, 1322),  # auto sem-all Campground <-> Backcountry Camping Area
    (1300, 1323),  # auto sem-all Campground <-> Group Camping Area
    (1300, 1765),  # auto sem-all Campground <-> Educational Camp
    (1307, 1324),  # auto sem-all Information <-> Information Board
    (1307, 1325),  # auto sem-all Information <-> Guidepost
    (1307, 1326),  # auto sem-all Information <-> Map
    (1307, 1327),  # auto sem-all Information <-> Visitor Center
    (1307, 1329),  # auto sem-all Information <-> Trail Marker
    (1307, 1330),  # auto sem-all Information <-> Information Terminal
    (1307, 1335),  # auto sem-all Information <-> Welcome Sign
    (1316, 1317),  # auto sem-all Bust <-> Graffiti
    (1316, 1318),  # auto sem-all Bust <-> Art Installation
    (1316, 1319),  # auto sem-all Bust <-> Sculpture
    (1316, 1320),  # auto sem-all Bust <-> Statue
    (1316, 2352),  # auto sem-all Bust <-> Street Art
    (1317, 1318),  # auto sem-all Graffiti <-> Art Installation
    (1317, 1319),  # auto sem-all Graffiti <-> Sculpture
    (1317, 1320),  # auto sem-all Graffiti <-> Statue
    (1317, 2352),  # auto sem-all Graffiti <-> Street Art
    (1318, 1319),  # auto sem-all Art Installation <-> Sculpture
    (1318, 1320),  # auto sem-all Art Installation <-> Statue
    (1318, 2352),  # auto sem-all Art Installation <-> Street Art
    (1319, 1320),  # auto sem-all Sculpture <-> Statue
    (1319, 2352),  # auto sem-all Sculpture <-> Street Art
    (1320, 2352),  # auto sem-all Statue <-> Street Art
    (1322, 1323),  # auto sem-all Backcountry Camping Area <-> Group Camping Area
    (1322, 1765),  # auto sem-all Backcountry Camping Area <-> Educational Camp
    (1323, 1765),  # auto sem-all Group Camping Area <-> Educational Camp
    (1324, 1325),  # auto sem-all Information Board <-> Guidepost
    (1324, 1326),  # auto sem-all Information Board <-> Map
    (1324, 1327),  # auto sem-all Information Board <-> Visitor Center
    (1324, 1329),  # auto sem-all Information Board <-> Trail Marker
    (1324, 1330),  # auto sem-all Information Board <-> Information Terminal
    (1324, 1335),  # auto sem-all Information Board <-> Welcome Sign
    (1325, 1326),  # auto sem-all Guidepost <-> Map
    (1325, 1327),  # auto sem-all Guidepost <-> Visitor Center
    (1325, 1329),  # auto sem-all Guidepost <-> Trail Marker
    (1325, 1330),  # auto sem-all Guidepost <-> Information Terminal
    (1325, 1335),  # auto sem-all Guidepost <-> Welcome Sign
    (1326, 1327),  # auto sem-all Map <-> Visitor Center
    (1326, 1329),  # auto sem-all Map <-> Trail Marker
    (1326, 1330),  # auto sem-all Map <-> Information Terminal
    (1326, 1335),  # auto sem-all Map <-> Welcome Sign
    (1327, 1330),  # auto sem-all Visitor Center <-> Information Terminal
    (1329, 1330),  # auto sem-all Trail Marker <-> Information Terminal
    (1330, 1335),  # auto sem-all Information Terminal <-> Welcome Sign
    (1424, 1493),  # auto sem-all Iron and Steel Industry <-> Business Manufacturing and Supply
    (1424, 1602),  # auto sem-all Iron and Steel Industry <-> Chemical Plant
    (1424, 1603),  # auto sem-all Iron and Steel Industry <-> Motorcycle Manufacturer
    (1424, 1664),  # auto sem-all Iron and Steel Industry <-> Auto Manufacturers and Distributors
    (1424, 1693),  # auto sem-all Iron and Steel Industry <-> Glass Manufacturer
    (1424, 1818),  # auto sem-all Iron and Steel Industry <-> Mattress Manufacturing
    (1424, 2007),  # auto sem-all Iron and Steel Industry <-> Aircraft Manufacturer
    (1424, 2105),  # auto sem-all Iron and Steel Industry <-> Furniture Manufacturers
    (1424, 2109),  # auto sem-all Iron and Steel Industry <-> Textile Mill
    (1424, 2382),  # auto sem-all Iron and Steel Industry <-> Steel Fabricators
    (1424, 2401),  # auto sem-all Iron and Steel Industry <-> Cotton Mill
    (1424, 2506),  # auto sem-all Iron and Steel Industry <-> Jewelry Manufacturer
    (1428, 1644),  # auto sem-all Jet Skis Rental <-> Canoe and Kayak Hire Service
    (1449, 2332),  # auto sem-all Event Photography <-> Real Estate Photography
    (1452, 2099),  # auto sem-all Farmers Market <-> Holiday Market
    (1452, 2137),  # auto sem-all Farmers Market <-> Seafood Market
    (1493, 1602),  # auto sem-all Business Manufacturing and Supply <-> Chemical Plant
    (1493, 1603),  # auto sem-all Business Manufacturing and Supply <-> Motorcycle Manufacturer
    (1493, 1664),  # auto sem-all Business Manufacturing and Supply <-> Auto Manufacturers and Distributors
    (1493, 1693),  # auto sem-all Business Manufacturing and Supply <-> Glass Manufacturer
    (1493, 1818),  # auto sem-all Business Manufacturing and Supply <-> Mattress Manufacturing
    (1493, 2007),  # auto sem-all Business Manufacturing and Supply <-> Aircraft Manufacturer
    (1493, 2089),  # auto sem-all Business Manufacturing and Supply <-> Leather Products Manufacturer
    (1493, 2105),  # auto sem-all Business Manufacturing and Supply <-> Furniture Manufacturers
    (1493, 2109),  # auto sem-all Business Manufacturing and Supply <-> Textile Mill
    (1493, 2319),  # auto sem-all Business Manufacturing and Supply <-> Shoe Factory
    (1493, 2382),  # auto sem-all Business Manufacturing and Supply <-> Steel Fabricators
    (1493, 2401),  # auto sem-all Business Manufacturing and Supply <-> Cotton Mill
    (1493, 2406),  # auto sem-all Business Manufacturing and Supply <-> Lighting Fixture Manufacturers
    (1493, 2506),  # auto sem-all Business Manufacturing and Supply <-> Jewelry Manufacturer
    (1493, 2626),  # auto sem-all Business Manufacturing and Supply <-> Cosmetic Products Manufacturer
    (1531, 1602),  # auto sem-all Plastic Manufacturer <-> Chemical Plant
    (1531, 1603),  # auto sem-all Plastic Manufacturer <-> Motorcycle Manufacturer
    (1531, 1664),  # auto sem-all Plastic Manufacturer <-> Auto Manufacturers and Distributors
    (1531, 1818),  # auto sem-all Plastic Manufacturer <-> Mattress Manufacturing
    (1531, 2007),  # auto sem-all Plastic Manufacturer <-> Aircraft Manufacturer
    (1531, 2089),  # auto sem-all Plastic Manufacturer <-> Leather Products Manufacturer
    (1531, 2105),  # auto sem-all Plastic Manufacturer <-> Furniture Manufacturers
    (1531, 2109),  # auto sem-all Plastic Manufacturer <-> Textile Mill
    (1531, 2319),  # auto sem-all Plastic Manufacturer <-> Shoe Factory
    (1531, 2382),  # auto sem-all Plastic Manufacturer <-> Steel Fabricators
    (1531, 2401),  # auto sem-all Plastic Manufacturer <-> Cotton Mill
    (1531, 2406),  # auto sem-all Plastic Manufacturer <-> Lighting Fixture Manufacturers
    (1531, 2506),  # auto sem-all Plastic Manufacturer <-> Jewelry Manufacturer
    (1531, 2626),  # auto sem-all Plastic Manufacturer <-> Cosmetic Products Manufacturer
    (1559, 1689),  # auto sem-all Dog Trainer <-> Horse Trainer
    (1559, 2492),  # auto sem-all Dog Trainer <-> Pet Training
    (1602, 1603),  # auto sem-all Chemical Plant <-> Motorcycle Manufacturer
    (1602, 1693),  # auto sem-all Chemical Plant <-> Glass Manufacturer
    (1602, 1818),  # auto sem-all Chemical Plant <-> Mattress Manufacturing
    (1602, 2007),  # auto sem-all Chemical Plant <-> Aircraft Manufacturer
    (1602, 2089),  # auto sem-all Chemical Plant <-> Leather Products Manufacturer
    (1602, 2105),  # auto sem-all Chemical Plant <-> Furniture Manufacturers
    (1602, 2109),  # auto sem-all Chemical Plant <-> Textile Mill
    (1602, 2319),  # auto sem-all Chemical Plant <-> Shoe Factory
    (1602, 2382),  # auto sem-all Chemical Plant <-> Steel Fabricators
    (1602, 2401),  # auto sem-all Chemical Plant <-> Cotton Mill
    (1602, 2406),  # auto sem-all Chemical Plant <-> Lighting Fixture Manufacturers
    (1602, 2506),  # auto sem-all Chemical Plant <-> Jewelry Manufacturer
    (1602, 2626),  # auto sem-all Chemical Plant <-> Cosmetic Products Manufacturer
    (1603, 1664),  # auto sem-all Motorcycle Manufacturer <-> Auto Manufacturers and Distributors
    (1603, 1693),  # auto sem-all Motorcycle Manufacturer <-> Glass Manufacturer
    (1603, 1818),  # auto sem-all Motorcycle Manufacturer <-> Mattress Manufacturing
    (1603, 2007),  # auto sem-all Motorcycle Manufacturer <-> Aircraft Manufacturer
    (1603, 2089),  # auto sem-all Motorcycle Manufacturer <-> Leather Products Manufacturer
    (1603, 2105),  # auto sem-all Motorcycle Manufacturer <-> Furniture Manufacturers
    (1603, 2109),  # auto sem-all Motorcycle Manufacturer <-> Textile Mill
    (1603, 2319),  # auto sem-all Motorcycle Manufacturer <-> Shoe Factory
    (1603, 2382),  # auto sem-all Motorcycle Manufacturer <-> Steel Fabricators
    (1603, 2401),  # auto sem-all Motorcycle Manufacturer <-> Cotton Mill
    (1603, 2406),  # auto sem-all Motorcycle Manufacturer <-> Lighting Fixture Manufacturers
    (1603, 2506),  # auto sem-all Motorcycle Manufacturer <-> Jewelry Manufacturer
    (1603, 2626),  # auto sem-all Motorcycle Manufacturer <-> Cosmetic Products Manufacturer
    (1625, 2623),  # auto sem-all Health Food Restaurant <-> Brasserie
    (1664, 1693),  # auto sem-all Auto Manufacturers and Distributors <-> Glass Manufacturer
    (1664, 1818),  # auto sem-all Auto Manufacturers and Distributors <-> Mattress Manufacturing
    (1664, 2007),  # auto sem-all Auto Manufacturers and Distributors <-> Aircraft Manufacturer
    (1664, 2089),  # auto sem-all Auto Manufacturers and Distributors <-> Leather Products Manufacturer
    (1664, 2105),  # auto sem-all Auto Manufacturers and Distributors <-> Furniture Manufacturers
    (1664, 2109),  # auto sem-all Auto Manufacturers and Distributors <-> Textile Mill
    (1664, 2319),  # auto sem-all Auto Manufacturers and Distributors <-> Shoe Factory
    (1664, 2382),  # auto sem-all Auto Manufacturers and Distributors <-> Steel Fabricators
    (1664, 2401),  # auto sem-all Auto Manufacturers and Distributors <-> Cotton Mill
    (1664, 2406),  # auto sem-all Auto Manufacturers and Distributors <-> Lighting Fixture Manufacturers
    (1664, 2506),  # auto sem-all Auto Manufacturers and Distributors <-> Jewelry Manufacturer
    (1664, 2626),  # auto sem-all Auto Manufacturers and Distributors <-> Cosmetic Products Manufacturer
    (1689, 2492),  # auto sem-all Horse Trainer <-> Pet Training
    (1693, 1818),  # auto sem-all Glass Manufacturer <-> Mattress Manufacturing
    (1693, 2007),  # auto sem-all Glass Manufacturer <-> Aircraft Manufacturer
    (1693, 2089),  # auto sem-all Glass Manufacturer <-> Leather Products Manufacturer
    (1693, 2105),  # auto sem-all Glass Manufacturer <-> Furniture Manufacturers
    (1693, 2109),  # auto sem-all Glass Manufacturer <-> Textile Mill
    (1693, 2319),  # auto sem-all Glass Manufacturer <-> Shoe Factory
    (1693, 2382),  # auto sem-all Glass Manufacturer <-> Steel Fabricators
    (1693, 2401),  # auto sem-all Glass Manufacturer <-> Cotton Mill
    (1693, 2406),  # auto sem-all Glass Manufacturer <-> Lighting Fixture Manufacturers
    (1693, 2506),  # auto sem-all Glass Manufacturer <-> Jewelry Manufacturer
    (1693, 2626),  # auto sem-all Glass Manufacturer <-> Cosmetic Products Manufacturer
    (1734, 2430),  # auto sem-all Poultry Farm <-> Pig Farm
    (1749, 1877),  # auto sem-all Health Spa <-> Medical Spa
    (1749, 2270),  # auto sem-all Health Spa <-> Float Spa
    (1807, 2198),  # auto sem-all Mining <-> Rice Mill
    (1807, 2229),  # auto sem-all Mining <-> Scrap Metals
    (1807, 2540),  # auto sem-all Mining <-> Mills
    (1818, 2007),  # auto sem-all Mattress Manufacturing <-> Aircraft Manufacturer
    (1818, 2089),  # auto sem-all Mattress Manufacturing <-> Leather Products Manufacturer
    (1818, 2105),  # auto sem-all Mattress Manufacturing <-> Furniture Manufacturers
    (1818, 2109),  # auto sem-all Mattress Manufacturing <-> Textile Mill
    (1818, 2319),  # auto sem-all Mattress Manufacturing <-> Shoe Factory
    (1818, 2382),  # auto sem-all Mattress Manufacturing <-> Steel Fabricators
    (1818, 2401),  # auto sem-all Mattress Manufacturing <-> Cotton Mill
    (1818, 2406),  # auto sem-all Mattress Manufacturing <-> Lighting Fixture Manufacturers
    (1818, 2506),  # auto sem-all Mattress Manufacturing <-> Jewelry Manufacturer
    (1818, 2626),  # auto sem-all Mattress Manufacturing <-> Cosmetic Products Manufacturer
    (1840, 2033),  # auto sem-all First Aid Class <-> Adult Education
    (1840, 2250),  # auto sem-all First Aid Class <-> Cpr Classes
    (1840, 2320),  # auto sem-all First Aid Class <-> Food Safety Training
    (1840, 2339),  # auto sem-all First Aid Class <-> Photography Classes
    (1840, 2499),  # auto sem-all First Aid Class <-> Firearm Training
    (1840, 2564),  # auto sem-all First Aid Class <-> Circus School
    (1877, 2270),  # auto sem-all Medical Spa <-> Float Spa
    (1965, 2623),  # auto sem-all Gluten Free Restaurant <-> Brasserie
    (1988, 2120),  # auto sem-all Animation Studio <-> Recording and Rehearsal Studio
    (1988, 2436),  # auto sem-all Animation Studio <-> Art Space Rental
    (2007, 2089),  # auto sem-all Aircraft Manufacturer <-> Leather Products Manufacturer
    (2007, 2105),  # auto sem-all Aircraft Manufacturer <-> Furniture Manufacturers
    (2007, 2109),  # auto sem-all Aircraft Manufacturer <-> Textile Mill
    (2007, 2319),  # auto sem-all Aircraft Manufacturer <-> Shoe Factory
    (2007, 2382),  # auto sem-all Aircraft Manufacturer <-> Steel Fabricators
    (2007, 2401),  # auto sem-all Aircraft Manufacturer <-> Cotton Mill
    (2007, 2406),  # auto sem-all Aircraft Manufacturer <-> Lighting Fixture Manufacturers
    (2007, 2506),  # auto sem-all Aircraft Manufacturer <-> Jewelry Manufacturer
    (2007, 2626),  # auto sem-all Aircraft Manufacturer <-> Cosmetic Products Manufacturer
    (2014, 2543),  # auto sem-all Natural Gas Supplier <-> Truck Gas Station
    (2033, 2250),  # auto sem-all Adult Education <-> Cpr Classes
    (2033, 2320),  # auto sem-all Adult Education <-> Food Safety Training
    (2033, 2339),  # auto sem-all Adult Education <-> Photography Classes
    (2033, 2499),  # auto sem-all Adult Education <-> Firearm Training
    (2082, 2370),  # auto sem-all Bike Sharing <-> Party Bike Rental
    (2089, 2105),  # auto sem-all Leather Products Manufacturer <-> Furniture Manufacturers
    (2089, 2109),  # auto sem-all Leather Products Manufacturer <-> Textile Mill
    (2089, 2319),  # auto sem-all Leather Products Manufacturer <-> Shoe Factory
    (2089, 2382),  # auto sem-all Leather Products Manufacturer <-> Steel Fabricators
    (2089, 2401),  # auto sem-all Leather Products Manufacturer <-> Cotton Mill
    (2089, 2406),  # auto sem-all Leather Products Manufacturer <-> Lighting Fixture Manufacturers
    (2089, 2506),  # auto sem-all Leather Products Manufacturer <-> Jewelry Manufacturer
    (2099, 2137),  # auto sem-all Holiday Market <-> Seafood Market
    (2105, 2109),  # auto sem-all Furniture Manufacturers <-> Textile Mill
    (2105, 2319),  # auto sem-all Furniture Manufacturers <-> Shoe Factory
    (2105, 2382),  # auto sem-all Furniture Manufacturers <-> Steel Fabricators
    (2105, 2401),  # auto sem-all Furniture Manufacturers <-> Cotton Mill
    (2105, 2406),  # auto sem-all Furniture Manufacturers <-> Lighting Fixture Manufacturers
    (2105, 2506),  # auto sem-all Furniture Manufacturers <-> Jewelry Manufacturer
    (2105, 2626),  # auto sem-all Furniture Manufacturers <-> Cosmetic Products Manufacturer
    (2109, 2319),  # auto sem-all Textile Mill <-> Shoe Factory
    (2109, 2382),  # auto sem-all Textile Mill <-> Steel Fabricators
    (2109, 2401),  # auto sem-all Textile Mill <-> Cotton Mill
    (2109, 2406),  # auto sem-all Textile Mill <-> Lighting Fixture Manufacturers
    (2109, 2506),  # auto sem-all Textile Mill <-> Jewelry Manufacturer
    (2109, 2626),  # auto sem-all Textile Mill <-> Cosmetic Products Manufacturer
    (2150, 2575),  # auto sem-all Town Car Service <-> Pedicab Service
    (2198, 2229),  # auto sem-all Rice Mill <-> Scrap Metals
    (2198, 2540),  # auto sem-all Rice Mill <-> Mills
    (2250, 2320),  # auto sem-all Cpr Classes <-> Food Safety Training
    (2250, 2339),  # auto sem-all Cpr Classes <-> Photography Classes
    (2250, 2499),  # auto sem-all Cpr Classes <-> Firearm Training
    (2250, 2564),  # auto sem-all Cpr Classes <-> Circus School
    (2319, 2382),  # auto sem-all Shoe Factory <-> Steel Fabricators
    (2319, 2401),  # auto sem-all Shoe Factory <-> Cotton Mill
    (2319, 2406),  # auto sem-all Shoe Factory <-> Lighting Fixture Manufacturers
    (2319, 2506),  # auto sem-all Shoe Factory <-> Jewelry Manufacturer
    (2319, 2626),  # auto sem-all Shoe Factory <-> Cosmetic Products Manufacturer
    (2320, 2339),  # auto sem-all Food Safety Training <-> Photography Classes
    (2320, 2499),  # auto sem-all Food Safety Training <-> Firearm Training
    (2320, 2564),  # auto sem-all Food Safety Training <-> Circus School
    (2339, 2499),  # auto sem-all Photography Classes <-> Firearm Training
    (2339, 2564),  # auto sem-all Photography Classes <-> Circus School
    (2382, 2401),  # auto sem-all Steel Fabricators <-> Cotton Mill
    (2382, 2406),  # auto sem-all Steel Fabricators <-> Lighting Fixture Manufacturers
    (2382, 2506),  # auto sem-all Steel Fabricators <-> Jewelry Manufacturer
    (2382, 2626),  # auto sem-all Steel Fabricators <-> Cosmetic Products Manufacturer
    (2401, 2406),  # auto sem-all Cotton Mill <-> Lighting Fixture Manufacturers
    (2401, 2506),  # auto sem-all Cotton Mill <-> Jewelry Manufacturer
    (2401, 2626),  # auto sem-all Cotton Mill <-> Cosmetic Products Manufacturer
    (2406, 2506),  # auto sem-all Lighting Fixture Manufacturers <-> Jewelry Manufacturer
    (2406, 2626),  # auto sem-all Lighting Fixture Manufacturers <-> Cosmetic Products Manufacturer
    (2441, 2499),  # auto sem-all EMS Training <-> Firearm Training
    (2499, 2564),  # auto sem-all Firearm Training <-> Circus School
    (2506, 2626),  # auto sem-all Jewelry Manufacturer <-> Cosmetic Products Manufacturer
    (74, 1745),  # auto sem-all Car Rental <-> RV Rentals
    (102, 1495),  # auto sem-all Gas Station <-> Bus Station
    (409, 414),  # auto sem-all Transportation Building <-> Train Station Building
    (420, 465),  # auto sem-all Blacksmith <-> Locksmith
    (498, 2656),  # auto sem-all Main Entrance <-> Stair Entrance
    (57, 1734),  # auto sem-all Animal Breeding Facility <-> Poultry Farm
    (151, 298),  # auto sem-all Recycling Center <-> E-Waste Container
    (271, 290),  # auto sem-all Bicycle Inner Tube Vending Machine <-> Transit Ticket Vending Machine
    (280, 290),  # auto sem-all Flat Coin Vending Machine <-> Transit Ticket Vending Machine
    (285, 290),  # auto sem-all Gas Pump <-> Transit Ticket Vending Machine
    (290, 2143),  # auto sem-all Transit Ticket Vending Machine <-> Rental Kiosks
    (763, 1818),  # auto sem-all Factory <-> Mattress Manufacturing
    (763, 2105),  # auto sem-all Factory <-> Furniture Manufacturers
    (763, 2109),  # auto sem-all Factory <-> Textile Mill
    (763, 2382),  # auto sem-all Factory <-> Steel Fabricators
    (763, 2401),  # auto sem-all Factory <-> Cotton Mill
    (1424, 2089),  # auto sem-all Iron and Steel Industry <-> Leather Products Manufacturer
    (1424, 2319),  # auto sem-all Iron and Steel Industry <-> Shoe Factory
    (1424, 2406),  # auto sem-all Iron and Steel Industry <-> Lighting Fixture Manufacturers
    (1602, 1664),  # auto sem-all Chemical Plant <-> Auto Manufacturers and Distributors
    (134, 1867),  # auto sem-all Parking Lot <-> Automotive Storage Facility
    (172, 269),  # auto sem-all Restroom <-> Portable Toilet
    (191, 299),  # auto sem-all Recycling <-> Green Waste Container
    (218, 220),  # auto sem-all Multilevel Parking Garage <-> Street-side Parking
    (218, 2405),  # auto sem-all Multilevel Parking Garage <-> Valet Service
    (221, 1867),  # auto sem-all Underground Parking <-> Automotive Storage Facility
    (266, 2120),  # auto sem-all Radio Station <-> Recording and Rehearsal Studio
    (267, 2120),  # auto sem-all Television Station <-> Recording and Rehearsal Studio
    (268, 2120),  # auto sem-all Film Studio <-> Recording and Rehearsal Studio
    (282, 290),  # auto sem-all Excrement Bag Dispenser <-> Transit Ticket Vending Machine
    (301, 1927),  # auto sem-all Flush Toilets <-> Public Toilet
    (657, 2418),  # auto sem-all Industrial Area <-> Oil and Gas Exploration and Development
    (763, 1424),  # auto sem-all Factory <-> Iron and Steel Industry
    (763, 2406),  # auto sem-all Factory <-> Lighting Fixture Manufacturers
    (914, 920),  # auto sem-all Reed bed <-> Tidal Flat
    (917, 918),  # auto sem-all Coastal Salt Marsh <-> String Bog
    (917, 922),  # auto sem-all Coastal Salt Marsh <-> Wet Meadow
    (1180, 1320),  # auto sem-all Artwork <-> Statue
    (1327, 1329),  # auto sem-all Visitor Center <-> Trail Marker
    (1424, 1531),  # auto sem-all Iron and Steel Industry <-> Plastic Manufacturer
    (1424, 2626),  # auto sem-all Iron and Steel Industry <-> Cosmetic Products Manufacturer
    (2033, 2441),  # auto sem-all Adult Education <-> EMS Training
    (2229, 2540),  # auto sem-all Scrap Metals <-> Mills
    (2250, 2441),  # auto sem-all Cpr Classes <-> EMS Training
    (2320, 2441),  # auto sem-all Food Safety Training <-> EMS Training
    (2339, 2441),  # auto sem-all Photography Classes <-> EMS Training
    (2441, 2564),  # auto sem-all EMS Training <-> Circus School
    (1871, 2573),  # auto sem-all Sex Therapist <-> Stress Management Services
    (763, 1493),  # auto sem-all Factory <-> Business Manufacturing and Supply
    (522, 525),  # auto sem-all Physiotherapist <-> Psychotherapist
    (624, 632),  # auto sem-all Historic Fort <-> Historic Fortress
    (172, 302),  # auto sem-all Restroom <-> Pit Latrine
    (219, 221),  # auto sem-all Park & Ride Lot <-> Underground Parking
    (220, 1867),  # auto sem-all Street-side Parking <-> Automotive Storage Facility
    (269, 302),  # auto sem-all Portable Toilet <-> Pit Latrine
    (695, 2086),  # auto sem-all Dance School <-> Country Dance Hall
    (914, 917),  # auto sem-all Reed bed <-> Coastal Salt Marsh
    (917, 920),  # auto sem-all Coastal Salt Marsh <-> Tidal Flat
    (1327, 1335),  # auto sem-all Visitor Center <-> Welcome Sign
    (1329, 1335),  # auto sem-all Trail Marker <-> Welcome Sign
    (1594, 2137),  # auto sem-all Agricultural Cooperatives <-> Seafood Market
    (1807, 2418),  # auto sem-all Mining <-> Oil and Gas Exploration and Development
    (1840, 2441),  # auto sem-all First Aid Class <-> EMS Training
    (1867, 2405),  # auto sem-all Automotive Storage Facility <-> Valet Service
    (2120, 2436),  # auto sem-all Recording and Rehearsal Studio <-> Art Space Rental
    (2198, 2418),  # auto sem-all Rice Mill <-> Oil and Gas Exploration and Development
    (763, 1664),  # auto sem-all Factory <-> Auto Manufacturers and Distributors
    (102, 1391),  # auto sem-all Gas Station <-> Marine Fuel Station
    (181, 2555),  # auto sem-all Garbage Dumpster <-> Hazardous Waste Disposal
    (191, 298),  # auto sem-all Recycling <-> E-Waste Container
    (219, 220),  # auto sem-all Park & Ride Lot <-> Street-side Parking
    (219, 2405),  # auto sem-all Park & Ride Lot <-> Valet Service
    (302, 1927),  # auto sem-all Pit Latrine <-> Public Toilet
    (369, 2684),  # auto sem-all Hospital Building <-> Hospital
    (397, 1036),  # auto sem-all Roof <-> Solar Panel Canopy
    (409, 1463),  # auto sem-all Transportation Building <-> Transportation
    (410, 2667),  # auto sem-all University Building <-> University Office
    (450, 2547),  # auto sem-all Plumber <-> Backflow Services
    (572, 1621),  # auto sem-all Trailhead <-> Mountain Bike Trails
    (728, 783),  # auto sem-all Racetrack (Non-Motorsport) <-> Cycling Track
    (728, 786),  # auto sem-all Racetrack (Non-Motorsport) <-> Running Track
    (957, 1248),  # auto sem-all Religious Office <-> Religious Store
    (960, 2624),  # auto sem-all Tax Advisor Office <-> Tax Office
    (1523, 2425),  # auto sem-all Plastic Surgeon <-> Phlebologist
    (1549, 2062),  # auto sem-all Disability Services and Support Organization <-> Veterans Organization
    (1583, 2425),  # auto sem-all Osteopathic Physician <-> Phlebologist
    (1594, 2099),  # auto sem-all Agricultural Cooperatives <-> Holiday Market
    (1595, 2425),  # auto sem-all Orthopedist <-> Phlebologist
    (1645, 2102),  # auto sem-all Surf Shop <-> Surf Lifesaving Club
    (1665, 2425),  # auto sem-all Internal Medicine <-> Phlebologist
    (1673, 2425),  # auto sem-all Neurologist <-> Phlebologist
    (1675, 2425),  # auto sem-all Dermatologist <-> Phlebologist
    (1710, 2425),  # auto sem-all Ear Nose and Throat <-> Phlebologist
    (1755, 2425),  # auto sem-all Gastroenterologist <-> Phlebologist
    (1761, 1785),  # auto sem-all Crisis Intervention Services <-> Adoption Services
    (1785, 1823),  # auto sem-all Adoption Services <-> Senior Citizen Services
    (1785, 2124),  # auto sem-all Adoption Services <-> Foster Care Services
    (1805, 2425),  # auto sem-all Urologist <-> Phlebologist
    (1814, 2425),  # auto sem-all Hair Replacement <-> Phlebologist
    (1823, 2062),  # auto sem-all Senior Citizen Services <-> Veterans Organization
    (1829, 2425),  # auto sem-all Pulmonologist <-> Phlebologist
    (1837, 2425),  # auto sem-all Rheumatologist <-> Phlebologist
    (1855, 2425),  # auto sem-all Neuropathologist <-> Phlebologist
    (1856, 2425),  # auto sem-all Endodontist <-> Phlebologist
    (1858, 2014),  # auto sem-all Oil Change Station <-> Natural Gas Supplier
    (1859, 2425),  # auto sem-all Nephrologist <-> Phlebologist
    (1862, 2425),  # auto sem-all Cardiologist <-> Phlebologist
    (1866, 2425),  # auto sem-all Oncologist <-> Phlebologist
    (1876, 2425),  # auto sem-all Anesthesiologist <-> Phlebologist
    (1881, 2425),  # auto sem-all Gerontologist <-> Phlebologist
    (1892, 2425),  # auto sem-all Allergist <-> Phlebologist
    (1924, 2425),  # auto sem-all Endocrinologist <-> Phlebologist
    (1947, 2425),  # auto sem-all Psychiatrist <-> Phlebologist
    (1986, 2425),  # auto sem-all Proctologist <-> Phlebologist
    (2153, 2425),  # auto sem-all Sleep Specialist <-> Phlebologist
    (2155, 2425),  # auto sem-all Ultrasound Imaging Center <-> Phlebologist
    (2165, 2425),  # auto sem-all Undersea Hyperbaric Medicine <-> Phlebologist
    (2171, 2425),  # auto sem-all Immunodermatologist <-> Phlebologist
    (2172, 2425),  # auto sem-all Pediatric Nephrology <-> Phlebologist
    (2175, 2425),  # auto sem-all Pediatric Gastroenterology <-> Phlebologist
    (2229, 2418),  # auto sem-all Scrap Metals <-> Oil and Gas Exploration and Development
    (2233, 2425),  # auto sem-all Infectious Disease Specialist <-> Phlebologist
    (2240, 2425),  # auto sem-all Pain Management <-> Phlebologist
    (2251, 2425),  # auto sem-all Pediatric Endocrinology <-> Phlebologist
    (2263, 2425),  # auto sem-all Vascular Medicine <-> Phlebologist
    (2271, 2425),  # auto sem-all Preventive Medicine <-> Phlebologist
    (2272, 2425),  # auto sem-all Pediatric Neurology <-> Phlebologist
    (2284, 2425),  # auto sem-all Foot Care <-> Phlebologist
    (2285, 2425),  # auto sem-all Pediatric Infectious Disease <-> Phlebologist
    (2291, 2425),  # auto sem-all Spine Surgeon <-> Phlebologist
    (2303, 2541),  # auto sem-all Laboratory <-> Dental Laboratories
    (2349, 2425),  # auto sem-all Pediatric doctor <-> Phlebologist
    (2378, 2569),  # auto sem-all Emergency Pet Hospital <-> Holistic Animal Care
    (2413, 2425),  # auto sem-all Pediatric Pulmonology <-> Phlebologist
    (2418, 2540),  # auto sem-all Oil and Gas Exploration and Development <-> Mills
    (2425, 2434),  # auto sem-all Phlebologist <-> Toxicologist
    (2425, 2439),  # auto sem-all Phlebologist <-> Neurotologist
    (2425, 2447),  # auto sem-all Phlebologist <-> Occupational Medicine
    (2425, 2477),  # auto sem-all Phlebologist <-> Hair Loss Center
    (2425, 2483),  # auto sem-all Phlebologist <-> Endoscopist
    (2425, 2497),  # auto sem-all Phlebologist <-> Hepatologist
    (2425, 2503),  # auto sem-all Phlebologist <-> Osteopath
    (2425, 2517),  # auto sem-all Phlebologist <-> Psychomotor Therapist
    (2425, 2521),  # auto sem-all Phlebologist <-> Pediatric Cardiology
    (2425, 2537),  # auto sem-all Phlebologist <-> Cosmetic Surgeon
    (2425, 2544),  # auto sem-all Phlebologist <-> Otologist
    (2425, 2546),  # auto sem-all Phlebologist <-> Geriatric Medicine
    (2425, 2549),  # auto sem-all Phlebologist <-> Retina Specialist
    (2425, 2565),  # auto sem-all Phlebologist <-> Concierge Medicine
    (2425, 2568),  # auto sem-all Phlebologist <-> Environmental Medicine
    (2425, 2606),  # auto sem-all Phlebologist <-> Pediatric Orthopedic Surgery
    (2425, 2613),  # auto sem-all Phlebologist <-> Pediatric Oncology
    (2425, 2629),  # auto sem-all Phlebologist <-> Pediatric Surgery
    (1471, 2425),  # auto sem-all Obstetrician and Gynecologist <-> Phlebologist
    (2057, 2425),  # auto sem-all Cardiovascular and Thoracic Surgeon <-> Phlebologist
    (204, 1694),  # auto sem-all Office Building <-> Business
    (352, 413),  # auto sem-all Entrance <-> Entrance/Exit
    (388, 2367),  # auto sem-all Hotel Building <-> Ryokan
    (403, 724),  # auto sem-all Stadium Building <-> Stadium
    (409, 2013),  # auto sem-all Transportation Building <-> Pipeline Transportation
    (409, 2044),  # auto sem-all Transportation Building <-> Medical Transportation
    (430, 1160),  # auto sem-all Candy Maker <-> Candy Store
    (519, 2023),  # auto sem-all Medical Laboratory <-> Environmental Testing
    (519, 2303),  # auto sem-all Medical Laboratory <-> Laboratory
    (1391, 1858),  # auto sem-all Marine Fuel Station <-> Oil Change Station
    (1549, 1785),  # auto sem-all Disability Services and Support Organization <-> Adoption Services
    (1797, 1804),  # auto sem-all Skate Shop <-> Professional Sports League
    (1804, 2484),  # auto sem-all Professional Sports League <-> Golf Equipment
    (1804, 2635),  # auto sem-all Professional Sports League <-> Hockey Equipment
    (185, 936),  # auto sem-all RV Drinking Water <-> Marine Drinking Water
    (377, 536),  # auto sem-all Building Under Construction <-> Road Under Construction
    (731, 1528),  # auto sem-all Yoga Studio <-> Boot Camp
    (1412, 1528),  # auto sem-all Pilates Studio <-> Boot Camp
    (1528, 2046),  # auto sem-all Boot Camp <-> Barre Classes
    (1528, 2075),  # auto sem-all Boot Camp <-> Cardio Classes
    (107, 369),  # auto sem-all Hospital Grounds <-> Hospital Building
    (130, 410),  # auto sem-all University Grounds <-> University Building
    (130, 2667),  # auto sem-all University Grounds <-> University Office
    (158, 399),  # auto sem-all School Grounds <-> School Building
    (163, 1785),  # auto sem-all Social Facility <-> Adoption Services
    (318, 1354),  # auto sem-all Tourist Train <-> Train Route
    (388, 1306),  # auto sem-all Hotel Building <-> Hotel
    (399, 1456),  # auto sem-all School Building <-> High School
    (399, 1478),  # auto sem-all School Building <-> Middle School
    (399, 1562),  # auto sem-all School Building <-> Private School
    (399, 1573),  # auto sem-all School Building <-> Art School
    (399, 1579),  # auto sem-all School Building <-> Religious School
    (399, 1688),  # auto sem-all School Building <-> Bartending School
    (399, 1815),  # auto sem-all School Building <-> Cosmetology School
    (399, 2553),  # auto sem-all School Building <-> Charter School
    (403, 1627),  # auto sem-all Stadium Building <-> Tennis Stadium
    (403, 1678),  # auto sem-all Stadium Building <-> Basketball Stadium
    (403, 1860),  # auto sem-all Stadium Building <-> Baseball Stadium
    (403, 1916),  # auto sem-all Stadium Building <-> Rugby Stadium
    (666, 2395),  # auto sem-all Religious Area <-> Religious Items
    (1391, 2543),  # auto sem-all Marine Fuel Station <-> Truck Gas Station
    (1528, 1971),  # auto sem-all Boot Camp <-> Tai Chi Studio
    (1528, 2338),  # auto sem-all Boot Camp <-> Qi Gong Studio
    (1761, 2062),  # auto sem-all Crisis Intervention Services <-> Veterans Organization
    (1761, 2197),  # auto sem-all Crisis Intervention Services <-> Department Of Social Service
    (2023, 2076),  # auto sem-all Environmental Testing <-> Paternity Tests and Services
    (2062, 2124),  # auto sem-all Veterans Organization <-> Foster Care Services
    (2124, 2197),  # auto sem-all Foster Care Services <-> Department Of Social Service
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
