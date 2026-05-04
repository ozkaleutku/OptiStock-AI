import { useState, useEffect, useRef, useMemo } from 'react';

const BATCH_SIZE = 30;

/**
 * Custom hook for infinite scroll functionality
 * @param {Array} data - Full data array
 * @param {Object} filters - Filter object (resets visible count when changed)
 * @returns {Object} - { visibleData, hasMore, loaderRef, visibleCount, totalCount }
 */
export const useInfiniteScroll = (data, filters = {}) => {
    const [visibleCount, setVisibleCount] = useState(BATCH_SIZE);
    const loaderRef = useRef(null);

    // Slice data to visible count
    const visibleData = useMemo(() => data.slice(0, visibleCount), [data, visibleCount]);
    const hasMore = visibleCount < data.length;

    // Reset visible count when filters change
    useEffect(() => {
        setVisibleCount(BATCH_SIZE);
    }, [JSON.stringify(filters)]);

    // IntersectionObserver for loading more
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore) {
                    setVisibleCount(prev => prev + BATCH_SIZE);
                }
            },
            { threshold: 0.1 }
        );

        if (loaderRef.current) {
            observer.observe(loaderRef.current);
        }

        return () => observer.disconnect();
    }, [hasMore]);

    return {
        visibleData,
        hasMore,
        loaderRef,
        visibleCount: visibleData.length,
        totalCount: data.length
    };
};

export default useInfiniteScroll;
