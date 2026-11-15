
import { useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  type SpringOptions,
} from "framer-motion";
import type { ReactNode } from "react";
import "./MagnificationDock.css";

export type DockItemData = {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
};

type DockProps = {
  items: DockItemData[];
  distance?: number;
  baseItemSize?: number;
  magnification?: number;
  spring?: SpringOptions;
};

type DockItemProps = {
  item: DockItemData;
  mouseX: ReturnType<typeof useMotionValue<number>>;
  distance: number;
  baseItemSize: number;
  magnification: number;
  spring: SpringOptions;
};

function DockItem({
  item,
  mouseX,
  distance,
  baseItemSize,
  magnification,
  spring,
}: DockItemProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  const mouseDistance = useTransform(mouseX, (value) => {
    const rect = ref.current?.getBoundingClientRect();

    if (!rect || !Number.isFinite(value)) return distance;

    return value - (rect.left + rect.width / 2);
  });

  const targetSize = useTransform(
    mouseDistance,
    [-distance, 0, distance],
    [baseItemSize, magnification, baseItemSize]
  );

  const size = useSpring(targetSize, spring);

  const iconScale = useTransform(
    size,
    [baseItemSize, magnification],
    [1, 1.2]
  );

  return (
    <motion.button
      ref={ref}
      type="button"
      className={`dock-item ${item.active ? "active" : ""}`}
      style={{ width: size, height: size }}
      onClick={item.onClick}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      aria-label={item.label}
      aria-current={item.active ? "page" : undefined}
    >
      <motion.span className="dock-icon" style={{ scale: iconScale }}>
        {item.icon}
      </motion.span>

      <AnimatePresence>
        {showTooltip && (
          <motion.span
            className="dock-tooltip"
            role="tooltip"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
            >
            {item.label}
            </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  );
}

export function MagnificationDock({
  items,
  distance = 180,
  baseItemSize = 48,
  magnification = 68,
  spring = { mass: 0.1, stiffness: 150, damping: 12 },
}: DockProps) {
  const mouseX = useMotionValue(Number.POSITIVE_INFINITY);

  return (
    <nav className="dock-wrapper" aria-label="Main navigation">
      <motion.div
        className="dock-panel"
        onMouseMove={(event) => mouseX.set(event.clientX)}
        onMouseLeave={() => mouseX.set(Number.POSITIVE_INFINITY)}
        onTouchStart={() => mouseX.set(Number.POSITIVE_INFINITY)}
      >
        {items.map((item) => (
          <DockItem
            key={item.label}
            item={item}
            mouseX={mouseX}
            distance={distance}
            baseItemSize={baseItemSize}
            magnification={magnification}
            spring={spring}
          />
        ))}
      </motion.div>
    </nav>
  );
}

export default MagnificationDock;
