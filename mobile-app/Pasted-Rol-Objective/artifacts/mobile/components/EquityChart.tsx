import React, { useMemo } from "react";
import { View, StyleSheet, Text } from "react-native";
import { useColors } from "@/hooks/useColors";
import type { EquityPoint } from "@/context/TradingContext";

interface Props {
  data: EquityPoint[];
  height?: number;
  showLabels?: boolean;
}

export function EquityChart({ data, height = 100, showLabels = true }: Props) {
  const colors = useColors();

  const { points, minVal, maxVal, isPositive } = useMemo(() => {
    if (data.length < 2) return { points: [], minVal: 0, maxVal: 0, isPositive: true };
    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const isPos = data[data.length - 1].value >= data[0].value;

    const pts = data.map((d, i) => ({
      x: (i / (data.length - 1)) * 100,
      y: 100 - ((d.value - min) / range) * 100,
    }));

    return { points: pts, minVal: min, maxVal: max, isPositive: isPos };
  }, [data]);

  const lineColor = isPositive ? colors.profit : colors.loss;
  const fillColor = isPositive
    ? "rgba(74, 222, 128, 0.08)"
    : "rgba(248, 113, 113, 0.08)";

  if (points.length < 2) {
    return <View style={[styles.container, { height }]} />;
  }

  const chartPadding = 4;
  const chartHeight = height - (showLabels ? 24 : 0);

  return (
    <View style={[styles.container, { height }]}>
      <View style={[styles.chartArea, { height: chartHeight }]}>
        {points.map((pt, i) => {
          if (i === 0) return null;
          const prev = points[i - 1];
          const x1 = `${prev.x}%`;
          const x2 = `${pt.x}%`;
          const y1 = chartPadding + (prev.y / 100) * (chartHeight - chartPadding * 2);
          const y2 = chartPadding + (pt.y / 100) * (chartHeight - chartPadding * 2);
          const dx = pt.x - prev.x;
          const dy = y2 - y1;
          const length = Math.sqrt(
            (dx * 0.01 * 100) ** 2 + dy ** 2
          );
          const angle = Math.atan2(dy, dx * 0.01 * 100) * (180 / Math.PI);
          const segWidth = Math.abs(dx / 100);

          return (
            <View
              key={i}
              style={[
                styles.segment,
                {
                  left: x1 as any,
                  top: y1,
                  width: `${dx}%` as any,
                  backgroundColor: "transparent",
                },
              ]}
            >
              <View
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: 1.5,
                  backgroundColor: lineColor,
                  transform: [
                    { translateY: (y2 - y1) / 2 },
                    { rotate: `${Math.atan2(y2 - y1, 100) * (180 / Math.PI)}deg` },
                  ],
                  transformOrigin: "0 0",
                }}
              />
            </View>
          );
        })}

        {points.map((pt, i) => {
          if (i !== points.length - 1) return null;
          const x = `${pt.x}%`;
          const y = chartPadding + (pt.y / 100) * (chartHeight - chartPadding * 2);
          return (
            <View
              key="dot"
              style={[
                styles.dot,
                {
                  left: x as any,
                  top: y,
                  backgroundColor: lineColor,
                  shadowColor: lineColor,
                },
              ]}
            />
          );
        })}
      </View>

      {showLabels && (
        <View style={styles.labels}>
          <Text style={[styles.labelText, { color: colors.mutedForeground }]}>
            {minVal.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </Text>
          <Text style={[styles.labelText, { color: colors.mutedForeground }]}>
            {maxVal.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
  },
  chartArea: {
    width: "100%",
    position: "relative",
    overflow: "hidden",
  },
  segment: {
    position: "absolute",
    height: 2,
  },
  dot: {
    position: "absolute",
    width: 6,
    height: 6,
    borderRadius: 3,
    marginLeft: -3,
    marginTop: -3,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 4,
    elevation: 4,
  },
  labels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
  },
  labelText: {
    fontSize: 10,
    fontFamily: "Inter_400Regular",
    fontVariant: ["tabular-nums"],
  },
});
