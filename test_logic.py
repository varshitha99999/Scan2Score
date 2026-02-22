from utils.image_processing import process_image

results = process_image("test_marks.jpg")
print(f"Found {len(results)} marks.")
for r in results:
    print(f"Q{r['question_index']}: {r['label']} -> {r['mark']}")
