"""
Parallel processing utilities for handling multiple PDF files concurrently.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Dict, Any, Tuple
import streamlit as st


def process_files_parallel(
    files: List[Tuple[str, bytes]],
    process_func: Callable,
    max_workers: int = 4,
    show_progress: bool = True
) -> List[Dict[str, Any]]:
    """
    Process multiple files in parallel using ThreadPoolExecutor.

    Args:
        files: List of (filename, file_bytes) tuples
        process_func: Function to process each file, signature: (filename, bytes) -> dict
        max_workers: Maximum number of parallel workers
        show_progress: Whether to show progress bar in Streamlit

    Returns:
        List of results from process_func for each file
    """
    results = []

    if show_progress:
        progress_bar = st.progress(0)
        status_text = st.empty()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_func, filename, file_bytes): filename
            for filename, file_bytes in files
        }

        # Collect results as they complete
        completed = 0
        total = len(files)

        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                completed += 1

                if show_progress:
                    progress = completed / total
                    progress_bar.progress(progress)
                    status_text.text(f"Töödeldud: {completed}/{total} faili")

            except Exception as e:
                # Log error but continue processing other files
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': str(e),
                    'data': [],
                    'warnings': [f"Viga faili töötlemisel: {str(e)}"]
                })
                completed += 1

                if show_progress:
                    progress = completed / total
                    progress_bar.progress(progress)
                    status_text.text(f"Töödeldud: {completed}/{total} faili (viimane ebaõnnestus)")

    if show_progress:
        progress_bar.empty()
        status_text.empty()

    return results


def batch_process(
    items: List[Any],
    process_func: Callable,
    batch_size: int = 10,
    max_workers: int = 4
) -> List[Any]:
    """
    Process items in batches with parallel execution.

    Args:
        items: List of items to process
        process_func: Function to process each item
        batch_size: Size of each batch
        max_workers: Maximum number of parallel workers

    Returns:
        List of results
    """
    results = []

    # Split into batches
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    for batch in batches:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            batch_results = list(executor.map(process_func, batch))
            results.extend(batch_results)

    return results
