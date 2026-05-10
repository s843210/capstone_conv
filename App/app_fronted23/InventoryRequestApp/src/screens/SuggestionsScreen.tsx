import React from 'react';
import {SafeAreaView, Text, FlatList, Pressable, View} from 'react-native';
import {Suggestion, SuggestionsScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

type Props = SuggestionsScreenProps & {
  suggestions: Suggestion[];
};

export default function SuggestionsScreen({navigation, suggestions}: Props) {
  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>건의사항</Text>
      <Text style={styles.subtitle}>편의점 이용 중 불편한 점이나 개선 의견을 남겨주세요.</Text>

      <FlatList
        data={suggestions}
        keyExtractor={item => item.id}
        renderItem={({item}) => (
          <Pressable
            style={styles.card}
            onPress={() => navigation.navigate('SuggestionDetail', {suggestion: item})}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.cardMeta} numberOfLines={2}>
              {item.content}
            </Text>
            <View style={styles.statusRow}>
              <Text style={styles.cardMeta}>작성자: {item.writer}</Text>
              <Text style={styles.cardMeta}>{item.updatedAt ?? item.createdAt}</Text>
            </View>
          </Pressable>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>아직 등록된 건의사항이 없습니다.</Text>}
      />

      <Pressable style={styles.primaryBtn} onPress={() => navigation.navigate('SuggestionWrite')}>
        <Text style={styles.primaryBtnText}>건의사항 작성</Text>
      </Pressable>
    </SafeAreaView>
  );
}
