TfLiteStatus ResizeOutputTensor(TfLiteContext* context,
                                const TfLiteTensor* data,
                                const TfLiteTensor* segment_ids,
                                TfLiteTensor* output) {
  int max_index = -1;
  const int segment_id_size = segment_ids->dims->data[0];
  if (segment_id_size > 0) {
    max_index = segment_ids->data.i32[segment_id_size - 1];
  }
  const int data_rank = NumDimensions(data);
  TfLiteIntArray* output_shape = TfLiteIntArrayCreate(NumDimensions(data));
  output_shape->data[0] = max_index + 1;
  for (int i = 1; i < data_rank; ++i) {
    output_shape->data[i] = data->dims->data[i];
  }
  return context->ResizeTensor(context, output, output_shape);
}
