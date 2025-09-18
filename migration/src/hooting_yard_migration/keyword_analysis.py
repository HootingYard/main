"""Keyword frequency analysis for YouTube SEO optimization."""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, Set
import yaml
from hooting_yard_migration.state.archive_org import ArchiveOrgEpisode


class KeywordAnalyzer:
    """Analyzes word frequency across all episode full text for keyword extraction."""

    # Common words to exclude from keyword analysis
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'would', 'you', 'your', 'i', 'me',
        'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
        'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
        'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they',
        'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who',
        'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was',
        'were', 'being', 'been', 'have', 'has', 'had', 'having', 'do', 'does',
        'did', 'doing', 'will', 'would', 'should', 'could', 'ought', 'im',
        'youre', 'hes', 'shes', 'its', 'were', 'theyre', 'ive', 'youve',
        'weve', 'theyve', 'id', 'youd', 'hed', 'shed', 'wed', 'theyd',
        'ill', 'youll', 'hell', 'shell', 'well', 'theyll', 'isnt', 'arent',
        'wasnt', 'werent', 'hasnt', 'havent', 'hadnt', 'wont', 'wouldnt',
        'dont', 'doesnt', 'didnt', 'cant', 'couldnt', 'shouldnt', 'mustnt'
    }

    def __init__(self, state_dir: Path):
        """Initialize analyzer with state directory path."""
        self.state_dir = Path(state_dir)
        self.archive_org_dir = self.state_dir / "archive_org"

    def extract_words_from_text(self, text: str) -> Set[str]:
        """Extract normalized words from text, excluding stop words."""
        if not text:
            return set()

        # Convert to lowercase and extract words (letters only)
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter out stop words and very short words
        return {word for word in words if word not in self.STOP_WORDS and len(word) >= 3}

    def load_all_episodes(self) -> Dict[str, ArchiveOrgEpisode]:
        """Load all episodes from state files."""
        episodes = {}

        if not self.archive_org_dir.exists():
            print(f"Archive.org state directory not found: {self.archive_org_dir}")
            return episodes

        # Scan all year directories
        for year_dir in self.archive_org_dir.iterdir():
            if not year_dir.is_dir():
                continue

            # Load all YAML files in year directory
            for yaml_file in year_dir.glob("*.yaml"):
                try:
                    episode = ArchiveOrgEpisode.load_from_yaml(yaml_file)
                    episodes[episode.identifier] = episode
                    print(f"Loaded episode: {episode.identifier}")
                except Exception as e:
                    print(f"Error loading {yaml_file}: {e}")

        return episodes

    def analyze_word_frequencies(self, episodes: Dict[str, ArchiveOrgEpisode]) -> Dict[str, int]:
        """Analyze word frequencies across all episode full text."""
        word_counter = Counter()
        total_episodes = len(episodes)
        processed_episodes = 0

        for episode in episodes.values():
            processed_episodes += 1
            if processed_episodes % 50 == 0:
                print(f"Processing episode {processed_episodes}/{total_episodes}: {episode.identifier}")

            # Extract words from full text
            if episode.full_text:
                words = self.extract_words_from_text(episode.full_text)
                word_counter.update(words)

            # Also extract words from title and description for completeness
            title_words = self.extract_words_from_text(episode.title)
            desc_words = self.extract_words_from_text(episode.description)
            word_counter.update(title_words)
            word_counter.update(desc_words)

        return dict(word_counter)

    def save_keyword_frequencies(self, word_frequencies: Dict[str, int]) -> Path:
        """Save word frequency analysis to keywords.yaml."""
        keywords_dir = self.state_dir / "keywords"
        keywords_dir.mkdir(exist_ok=True)

        keywords_file = keywords_dir / "keywords.yaml"

        # Sort by frequency (descending) for easier analysis
        sorted_frequencies = dict(sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True))

        # Create metadata about the analysis
        analysis_data = {
            'metadata': {
                'total_unique_words': len(sorted_frequencies),
                'analysis_date': '2025-09-19T00:00:00',
                'description': 'Word frequency analysis of Hooting Yard episode corpus for YouTube SEO'
            },
            'word_frequencies': sorted_frequencies
        }

        with open(keywords_file, 'w', encoding='utf-8') as f:
            yaml.dump(analysis_data, f, default_flow_style=False, allow_unicode=True)

        print(f"Saved {len(sorted_frequencies)} word frequencies to {keywords_file}")
        return keywords_file

    def run_analysis(self) -> Path:
        """Run complete keyword frequency analysis."""
        print("Starting keyword frequency analysis...")

        # Load all episodes
        print("Loading episodes from state files...")
        episodes = self.load_all_episodes()
        print(f"Loaded {len(episodes)} episodes")

        if not episodes:
            print("No episodes found. Make sure discovery has completed.")
            return None

        # Analyze word frequencies
        print("Analyzing word frequencies...")
        word_frequencies = self.analyze_word_frequencies(episodes)
        print(f"Found {len(word_frequencies)} unique words")

        # Save results
        keywords_file = self.save_keyword_frequencies(word_frequencies)

        # Print some stats
        total_words = sum(word_frequencies.values())
        print(f"Total word occurrences: {total_words}")

        # Show top 20 most frequent words
        sorted_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)
        print("\nTop 20 most frequent words:")
        for word, count in sorted_words[:20]:
            print(f"  {word}: {count}")

        return keywords_file


def analyze_keywords(state_dir: str) -> Path:
    """Convenience function to run keyword analysis."""
    analyzer = KeywordAnalyzer(Path(state_dir))
    return analyzer.run_analysis()