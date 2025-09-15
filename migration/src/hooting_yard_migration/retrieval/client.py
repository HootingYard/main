"""Archive.org API client."""

import json
import logging
from typing import Dict, Any, List, Optional
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from hooting_yard_migration.retrieval.models import (
    Episode,
    EpisodeMetadata,
    FileInfo,
)

logger = logging.getLogger(__name__)


class ArchiveOrgClient:
    """Client for interacting with Archive.org APIs."""

    BASE_URL = "https://archive.org"

    def __init__(self, timeout: int = 30):
        """Initialize the client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def get_episode_metadata(self, identifier: str) -> Episode:
        """Get complete metadata for an episode.

        Args:
            identifier: Archive.org item identifier (e.g., "hy0_hooting_yard_2004-04-14")

        Returns:
            Episode object with metadata and file information

        Raises:
            ValueError: If the identifier is invalid or episode not found
            URLError: If there's a network error
        """
        url = f"{self.BASE_URL}/metadata/{identifier}"
        logger.debug(f"Fetching metadata from: {url}")

        try:
            with urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read())
        except HTTPError as e:
            if e.code == 404:
                raise ValueError(f"Episode not found: {identifier}")
            raise
        except URLError as e:
            logger.error(f"Failed to fetch metadata for {identifier}: {e}")
            raise

        # Parse metadata
        if "metadata" not in data:
            raise ValueError(f"Invalid metadata response for {identifier}")

        metadata = EpisodeMetadata.from_archive_metadata(data["metadata"])

        # Parse files
        files = []
        for file_data in data.get("files", []):
            if "name" in file_data:  # Skip entries without names
                files.append(FileInfo.from_dict(file_data))

        return Episode(
            identifier=identifier,
            metadata=metadata,
            files=files,
            server=data.get("server", ""),
            dir=data.get("dir", ""),
        )

    def search_collection(
        self,
        collection: str = "hooting-yard",
        fields: Optional[List[str]] = None,
        rows: int = 100,
        page: int = 1,
        sort: str = "date asc",
    ) -> Dict[str, Any]:
        """Search for items in a collection.

        Args:
            collection: Collection name
            fields: Fields to return
            rows: Number of results per page
            page: Page number
            sort: Sort order

        Returns:
            Search results dictionary
        """
        if fields is None:
            fields = ["identifier", "title", "date", "description"]

        params = {
            "q": f"collection:{collection}",
            "fl": ",".join(fields),
            "sort": sort,
            "output": "json",
            "rows": rows,
            "page": page,
        }

        url = f"{self.BASE_URL}/advancedsearch.php?{urlencode(params)}"
        logger.debug(f"Searching collection: {url}")

        try:
            with urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read())
        except URLError as e:
            logger.error(f"Failed to search collection {collection}: {e}")
            raise

        return data

    def get_collection_count(self, collection: str = "hooting-yard") -> int:
        """Get the total number of items in a collection.

        Args:
            collection: Collection name

        Returns:
            Total item count
        """
        result = self.search_collection(collection, fields=["identifier"], rows=1)
        return result["response"]["numFound"]

    def get_all_episode_identifiers(
        self, collection: str = "hooting-yard"
    ) -> List[str]:
        """Get all episode identifiers from a collection.

        Args:
            collection: Collection name

        Returns:
            List of episode identifiers
        """
        identifiers = []
        page = 1
        rows_per_page = 100

        total = self.get_collection_count(collection)
        logger.info(f"Found {total} episodes in collection {collection}")

        while True:
            result = self.search_collection(
                collection,
                fields=["identifier"],
                rows=rows_per_page,
                page=page,
            )

            docs = result["response"]["docs"]
            if not docs:
                break

            for doc in docs:
                identifiers.append(doc["identifier"])

            if len(identifiers) >= total:
                break

            page += 1

        return identifiers