import 'dart:ui';

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

class WheelPopupField extends StatefulWidget {
  const WheelPopupField({
    super.key,
    required this.values,
    required this.selected,
    required this.labelOf,
    required this.onChanged,
    this.style,
    this.width = 96,
  });

  final List<int> values;
  final int selected;
  final String Function(int value) labelOf;
  final ValueChanged<int> onChanged;
  final TextStyle? style;
  final double width;

  @override
  State<WheelPopupField> createState() => _WheelPopupFieldState();
}

class _WheelPopupFieldState extends State<WheelPopupField> {
  static const _itemExtent = 40.0;
  static const _visibleRows = 5;

  final _link = LayerLink();
  final _portal = OverlayPortalController();
  FixedExtentScrollController? _controller;

  void _open() {
    _controller?.dispose();
    _controller = FixedExtentScrollController(
      initialItem: widget.values.indexOf(widget.selected),
    );
    _portal.show();
  }

  void _close() => _portal.hide();

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CompositedTransformTarget(
      link: _link,
      child: OverlayPortal(
        controller: _portal,
        overlayChildBuilder: (context) => Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: _close,
              ),
            ),
            CompositedTransformFollower(
              link: _link,
              targetAnchor: Alignment.center,
              followerAnchor: Alignment.center,
              child: Material(
                elevation: 8,
                borderRadius: BorderRadius.circular(12),
                clipBehavior: Clip.antiAlias,
                child: SizedBox(
                  width: widget.width,
                  height: _itemExtent * _visibleRows,
                  child: ScrollConfiguration(
                    behavior: ScrollConfiguration.of(context).copyWith(
                      dragDevices: {
                        PointerDeviceKind.touch,
                        PointerDeviceKind.mouse,
                        PointerDeviceKind.trackpad,
                        PointerDeviceKind.stylus,
                      },
                    ),
                    child: CupertinoPicker(
                      scrollController: _controller,
                      itemExtent: _itemExtent,
                      onSelectedItemChanged: (index) =>
                          widget.onChanged(widget.values[index]),
                      children: [
                        for (final value in widget.values)
                          Center(
                            child: Text(
                              widget.labelOf(value),
                              style: widget.style,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        child: InkWell(
          onTap: _open,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
            child: Text(widget.labelOf(widget.selected), style: widget.style),
          ),
        ),
      ),
    );
  }
}
