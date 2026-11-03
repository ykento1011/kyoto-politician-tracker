import { useRef } from 'react';

export function useSwipeToClose(onClose, threshold = 60) {
  const touchStartY = useRef(0);
  const isEligible = useRef(false);

  const handleTouchStart = (e) => {
    touchStartY.current = e.touches[0].clientY;
    isEligible.current = true;
  };

  const handleTouchMove = (e) => {
    if (!isEligible.current) return;
    const currentY = e.touches[0].clientY;
    if (currentY - touchStartY.current < 0) {
      isEligible.current = false;
    }
  };

  const handleTouchEnd = (e) => {
    if (!isEligible.current) return;
    const endY = e.changedTouches[0].clientY;
    const distanceY = endY - touchStartY.current;

    if (distanceY >= threshold) {
      onClose();
    }
    touchStartY.current = 0;
    isEligible.current = false;
  };

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
  };
}
