"""
Test prompts for record_unknown_question functionality

These prompts are designed to test different scenarios:
1. Out-of-scope questions (not related to Priyanshu's career/background)
2. General knowledge questions
3. Cooking/Recipe questions
4. Random trivia
5. Off-topic discussions
"""

TEST_PROMPTS = [
    # Out-of-scope general knowledge questions
    "What is the capital of France?",
    "How do I make biryani?",
    "What is the weather like today?",
    "Tell me a joke",
    "How to train a dog?",
    
    # Cooking/Recipe questions
    "How to make pasta?",
    "What's the recipe for samosa?",
    "How to bake a chocolate cake?",
    "Best way to cook rice?",
    "How to make chai?",
    
    # Random trivia
    "What's the largest planet?",
    "Who invented the telephone?",
    "What is photosynthesis?",
    "How far is Earth from the Sun?",
    "When was the internet invented?",
    
    # Personal but out-of-scope
    "What's your favorite movie?",
    "Do you like sports?",
    "What's your favorite color?",
    "Do you have a pet?",
    "Where do you live?",
    
    # Off-topic discussions
    "Let's talk about politics",
    "Tell me about cryptocurrency",
    "What do you think about AI ethics?",
    "Recommend a book",
    "What's a good vacation destination?",
    
    # Very short queries (should trigger alpha_num_chars < 20 detection)
    "xyz",
    "abc",
    "qwerty",
    
    # Relevant questions (should NOT trigger record)
    "What is your experience with Python?",
    "Tell me about your background",
    "What projects have you worked on?",
    "What are your skills?",
    "How can I contact you?",
]

if __name__ == "__main__":
    print("Test Prompts for record_unknown_question functionality\n")
    print("=" * 70)
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"{i:2d}. {prompt}")
    print("=" * 70)
    print(f"\nTotal prompts: {len(TEST_PROMPTS)}")
    print("\nInstructions:")
    print("1. Run the app: python app.py")
    print("2. Test each prompt in the Gradio chat interface")
    print("3. Check logs to see:")
    print("   - Which prompts trigger 'Detected SDK-like or malformed response'")
    print("   - Which prompts trigger 'Detected fallback phrase'")
    print("   - Telegram notification status (✓ or ✗)")
    print("\nExpected behavior:")
    print("- Prompts 1-34 should trigger notifications (out-of-scope)")
    print("- Prompts 35-39 should NOT trigger notifications (in-scope)")
