export interface TourStop {
  id: string;
  buildingId: string;
  title: string;
  subtitle: string;
  narration: string;
  targetOverride?: [number, number, number];
  cameraOffset?: [number, number, number];
}

export const TOUR_STOPS: TourStop[] = [
  {
    id: "main-gate",
    buildingId: "way/531088187",
    title: "Main Gate & Campus Entrance",
    subtitle: "Ettimadai Railway Station Road approach",
    narration:
      "Welcome to Amrita Vishwa Vidyapeetham, Ettimadai. Just inside the southern entry sits Dhanlaxmi Bank and ATM alongside the shaded main drive leading up into the academic core.",
    targetOverride: [-22, -4, 352],
    cameraOffset: [115, 98, 135],
  },
  {
    id: "ab1",
    buildingId: "way/380925364",
    title: "Academic Block 1 (AB-1)",
    subtitle: "School of Engineering",
    narration:
      "The flagship engineering quadrangle on the eastern side of campus, housing core labs, lecture halls, and Amriteshwari Hall right beside its courtyard.",
    cameraOffset: [120, 108, 128],
  },
  {
    id: "ab2",
    buildingId: "way/380702789",
    title: "Academic Block 2 (AB-2)",
    subtitle: "Computing, Sciences & Central Library",
    narration:
      "Rising into the central terrace, AB-2 wraps around landscaped inner courts with the Central Library and IT Canteen steps away to the east and west.",
    cameraOffset: [155, 138, 165],
  },
  {
    id: "ab3",
    buildingId: "way/380829415",
    title: "Academic Block 3 (AB-3)",
    subtitle: "School of Computing & International School of Law",
    narration:
      "Perched higher along the foothills at the north-west end of campus, AB-3 overlooks the valley and connects back to AB-2 via the tree-lined ridge road.",
    cameraOffset: [115, 102, 125],
  },
  {
    id: "main-canteen",
    buildingId: "way/546394562",
    title: "Main Canteen",
    subtitle: "Primary student dining hub",
    narration:
      "Tucked just south of AB-1 and Amriteshwari Hall, Main Canteen is the busiest mid-day stop for meals, snacks, and coffee between lectures.",
    cameraOffset: [78, 72, 86],
  },
  {
    id: "hostels-sports",
    buildingId: "way/380925366",
    title: "Hostels & Sports Ground",
    subtitle: "Bhavanams & Amrita Playground",
    narration:
      "On the eastern slope sit Yagnavalkya, Nachiketas, and Vyasa Maharishi Bhavanams, overlooking Amrita Playground, basketball courts, tennis courts, and the pool.",
    targetOverride: [330, 6, 75],
    cameraOffset: [175, 165, 225],
  },
];
