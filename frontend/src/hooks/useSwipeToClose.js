import { useRef, useCallback } from 'react';

/**
 * モバイルボトムシート用 Swipe-to-Close フック
 * @param {Function} onClose クローズ処理
 * @param {number} threshold スワイプ判定の最小移動量 (px, デフォルト 50px)
 * @param {React.RefObject} scrollContainerRef スクロール可能領域の ref
 */
export function useSwipeToClose({ onClose, threshold = 50, scrollContainerRef = null }) {
  const touchStartPos = useRef({ x: 0, y: 0 });
  const isSwipeActiveRef = useRef(false);

  const onTouchStart = useCallback((e) => {
    if (e.touches.length !== 1) return;
    const touch = e.touches[0];
    touchStartPos.current = { x: touch.clientX, y: touch.clientY };

    // スクロールコンテナが一番上 (scrollTop <= 0) にある場合のみスワイプを有効化
    if (scrollContainerRef && scrollContainerRef.current) {
      isSwipeActiveRef.current = scrollContainerRef.current.scrollTop <= 0;
    } else {
      isSwipeActiveRef.current = true;
    }
  }, [scrollContainerRef]);

  const onTouchMove = useCallback((e) => {
    if (!isSwipeActiveRef.current) return;
    // スクロール中にもし最上部より下へ移動していたらスワイプ無効化
    if (scrollContainerRef && scrollContainerRef.current && scrollContainerRef.current.scrollTop > 0) {
      isSwipeActiveRef.current = false;
    }
  }, [scrollContainerRef]);

  const onTouchEnd = useCallback((e) => {
    if (!isSwipeActiveRef.current) return;
    if (e.changedTouches.length !== 1) return;

    const touch = e.changedTouches[0];
    const deltaY = touch.clientY - touchStartPos.current.y;
    const deltaX = Math.abs(touch.clientX - touchStartPos.current.x);

    // 下方向へ threshold 以上移動し、かつ横方向よりも縦方向の移動量が大きい場合にクローズ
    if (deltaY >= threshold && deltaY > deltaX) {
      if (typeof onClose === 'function') {
        onClose();
      }
    }
    isSwipeActiveRef.current = false;
  }, [onClose, threshold]);

  return {
    onTouchStart,
    onTouchMove,
    onTouchEnd,
  };
}

export default useSwipeToClose;
