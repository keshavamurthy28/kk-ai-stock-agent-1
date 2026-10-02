# -------------------------------------------------------------------
            # ORDERFLOW DELTA & VOLUME BAR SUB-CHART
            # -------------------------------------------------------------------
            st.subheader("⚡ Minute/Hour Orderflow Delta & Volume Breakdown")

            fig_delta = go.Figure()

            # Color-code volume bars: Green for positive delta, Red for negative delta
            bar_colors = [
                "#26a69a" if val >= 0 else "#ef5350"
                for val in df_data["Delta"]
            ]

            fig_delta.add_trace(
                go.Bar(
                    x=df_data.index,
                    y=df_data["Delta"],
                    name="Period Delta (Buy - Sell)",
                    marker_color=bar_colors,
                )
            )

            # Optional: Add volume as an overlay or secondary view if desired
            fig_delta.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                template="plotly_white",
                yaxis_title="Delta Volume",
                xaxis_title="Time / Date",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            )
            st.plotly_chart(fig_delta, use_container_width=True)
